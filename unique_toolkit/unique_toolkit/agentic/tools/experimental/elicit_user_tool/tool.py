from __future__ import annotations

import asyncio
import json
from logging import getLogger
from typing import Any

import unique_sdk

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.experimental.elicit_user_tool.config import (
    ElicitUserToolConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

LOGGER = getLogger(__name__)

# Mirrors unique_sdk.cli.commands.elicitation.TERMINAL_STATUSES (no CLI import).
_TERMINAL_STATUSES = frozenset(
    {
        "RESPONDED",
        "ACCEPTED",
        "REJECTED",
        "DECLINED",
        "CANCELLED",
        "EXPIRED",
        "COMPLETED",
    }
)


def _parse_response_schema(raw: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Return (schema, error_message)."""
    if raw is None:
        return None, "response_schema is required"
    if isinstance(raw, dict):
        return raw, None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            return None, f"response_schema is not valid JSON: {exc}"
        if not isinstance(parsed, dict):
            return None, "response_schema JSON must be an object"
        return parsed, None
    return None, "response_schema must be a JSON object or JSON string"


async def _poll_until_terminal(
    *,
    user_id: str,
    company_id: str,
    elicitation_id: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[dict[str, Any], bool]:
    """Return (last_elicitation_dict, timed_out)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    last: dict[str, Any] = {}

    while True:
        elicitation = await unique_sdk.Elicitation.get_elicitation_async(
            user_id=user_id,
            company_id=company_id,
            elicitation_id=elicitation_id,
        )
        last = dict(elicitation)
        status = str(elicitation.get("status", "")).upper()
        if status in _TERMINAL_STATUSES:
            return last, False
        if loop.time() >= deadline:
            return last, True
        await asyncio.sleep(poll_interval_seconds)


class ElicitUserTool(Tool[ElicitUserToolConfig]):
    """Blocks until the user answers a FORM elicitation (or it terminates / times out)."""

    name = "AskUser"

    def __init__(
        self,
        config: ElicitUserToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ) -> None:
        super().__init__(config, event, tool_progress_reporter)
        self._event = event

    def takes_control(self) -> bool:
        """False: tool blocks until terminal status; loop must continue with the tool result."""
        return False

    def display_name(self) -> str:
        return self.config.display_name

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": (
                            'The question or prompt shown to the user (like elicit ask "<question>"). '
                            "Use for clarifications, confirmations before destructive steps, "
                            "missing parameters, choices, or structured forms."
                        ),
                    },
                    "tool_name": {
                        "type": "string",
                        "description": (
                            "Short snake_case label for this request (platform toolName); "
                            "default agent_question. Prefer meaningful names, e.g. "
                            "confirm_delete, choose_region, pick_report, clarify_scope."
                        ),
                    },
                    "response_schema": {
                        "type": "object",
                        "description": (
                            "Required JSON Schema for the form body (root type object). "
                            "Constructed by the agent per orchestrator instructions—not defaulted "
                            "by this tool. Use string+enum for dropdown; boolean for a confirmation "
                            "checkbox; array with items.type string and items.enum for multi-checkbox."
                        ),
                    },
                    "expires_in_seconds": {
                        "type": "integer",
                        "description": (
                            "Optional: seconds until the elicitation auto-expires on the platform "
                            "(like --expires-in on elicit ask)."
                        ),
                    },
                },
                "required": ["message", "response_schema"],
            },
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        args = tool_call.arguments or {}
        message = args.get("message")
        if not isinstance(message, str) or not message.strip():
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore[arg-type]
                name=self.name,
                error_message="message must be a non-empty string.",
            )

        schema, schema_err = _parse_response_schema(args.get("response_schema"))
        if schema_err or schema is None:
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore[arg-type]
                name=self.name,
                error_message=schema_err or "Invalid response_schema.",
            )

        tool_name_raw = args.get("tool_name")
        tool_name = (
            tool_name_raw.strip()
            if isinstance(tool_name_raw, str) and tool_name_raw.strip()
            else "agent_question"
        )

        expires_raw = args.get("expires_in_seconds")
        expires_in_seconds: int | None = None
        if expires_raw is not None:
            if isinstance(expires_raw, bool) or not isinstance(expires_raw, int):
                return ToolCallResponse(
                    id=tool_call.id,  # type: ignore[arg-type]
                    name=self.name,
                    error_message="expires_in_seconds must be an integer if provided.",
                )
            if expires_raw < 1:
                return ToolCallResponse(
                    id=tool_call.id,  # type: ignore[arg-type]
                    name=self.name,
                    error_message="expires_in_seconds must be >= 1 if provided.",
                )
            expires_in_seconds = expires_raw

        chat_id = self._event.payload.chat_id
        message_id = self._event.payload.assistant_message.id
        user_id = self._event.user_id
        company_id = self._event.company_id

        create_kwargs: dict[str, Any] = {
            "mode": "FORM",
            "message": message.strip(),
            "toolName": tool_name,
            "schema": schema,
            "chatId": chat_id,
            "messageId": message_id,
        }
        if expires_in_seconds is not None:
            create_kwargs["expiresInSeconds"] = expires_in_seconds

        try:
            created = await unique_sdk.Elicitation.create_elicitation_async(
                user_id=user_id,
                company_id=company_id,
                **create_kwargs,
            )
        except unique_sdk.APIError as exc:
            LOGGER.warning("AskUser: create_elicitation_async failed: %s", exc)
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore[arg-type]
                name=self.name,
                error_message=f"Failed to create elicitation: {exc}",
            )

        elicitation_id = created.get("id")
        if not isinstance(elicitation_id, str) or not elicitation_id:
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore[arg-type]
                name=self.name,
                error_message="Platform did not return an elicitation id.",
            )

        try:
            final, timed_out = await _poll_until_terminal(
                user_id=user_id,
                company_id=company_id,
                elicitation_id=elicitation_id,
                timeout_seconds=float(self.config.timeout_seconds),
                poll_interval_seconds=float(self.config.poll_interval_seconds),
            )
        except unique_sdk.APIError as exc:
            LOGGER.warning("AskUser: polling failed: %s", exc)
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore[arg-type]
                name=self.name,
                error_message=f"Failed while waiting for elicitation: {exc}",
            )

        status = str(final.get("status", "")).upper()
        payload: dict[str, Any] = {
            "elicitation_id": elicitation_id,
            "status": status or "UNKNOWN",
            "response": final.get("responseContent"),
            "timed_out": timed_out,
        }

        system_reminder = ""
        if timed_out:
            system_reminder = (
                "The elicitation wait timed out locally. Do not assume the user answered; "
                "retry AskUser only if still needed."
            )
        elif status in {"DECLINED", "CANCELLED", "EXPIRED"}:
            system_reminder = (
                "The user did not complete the elicitation successfully. Do not proceed "
                "with actions that required their confirmation or input."
            )

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore[arg-type]
            name=self.name,
            content=json.dumps(payload, ensure_ascii=False),
            system_reminder=system_reminder,
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        return []
