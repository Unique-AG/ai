"""Elicitation commands: create, list, get, respond, wait, and ask the user for input.

Elicitations are user-input requests routed through the Unique AI Platform.
They are the canonical mechanism for an agent (or tool) to pose a question to
the user and wait for a structured answer without leaving the conversation.

The CLI exposes both low-level operations (create / get / respond / list /
wait) and a high-level ``ask`` command that creates a FORM elicitation and
blocks until the user responds or the request expires/times out.
"""

from __future__ import annotations

import json
import time
from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import (
    format_elicitation,
    format_elicitation_response,
    format_pending_elicitations,
)
from unique_sdk.cli.state import ShellState

DEFAULT_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_WAIT_TIMEOUT_SECONDS = 300
TERMINAL_STATUSES = {"RESPONDED", "DECLINED", "CANCELLED", "EXPIRED", "COMPLETED"}


def _parse_json_arg(value: str | None, *, field: str) -> dict[str, Any] | None:
    """Parse an optional JSON string argument into a dict.

    Raises ``ValueError`` with a user-friendly message if the value is not
    valid JSON or does not decode to a JSON object.
    """
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON for {field}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field} must be a JSON object")
    return parsed


def _parse_metadata_pairs(
    metadata: list[tuple[str, str]] | None,
) -> dict[str, str] | None:
    """Convert a list of ``(key, value)`` pairs into a metadata dict."""
    if not metadata:
        return None
    return dict(metadata)


def _build_create_params(
    *,
    mode: str,
    message: str,
    tool_name: str,
    schema: dict[str, Any] | None,
    url: str | None,
    chat_id: str | None,
    message_id: str | None,
    expires_in_seconds: int | None,
    external_elicitation_id: str | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assemble the ``create_elicitation`` params dict, omitting None values."""
    params: dict[str, Any] = {
        "mode": mode,
        "message": message,
        "toolName": tool_name,
    }
    if schema is not None:
        params["schema"] = schema
    if url is not None:
        params["url"] = url
    if chat_id is not None:
        params["chatId"] = chat_id
    if message_id is not None:
        params["messageId"] = message_id
    if expires_in_seconds is not None:
        params["expiresInSeconds"] = expires_in_seconds
    if external_elicitation_id is not None:
        params["externalElicitationId"] = external_elicitation_id
    if metadata is not None:
        params["metadata"] = metadata
    return params


def cmd_elicit_create(
    state: ShellState,
    *,
    mode: str,
    message: str,
    tool_name: str,
    schema: str | None = None,
    url: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
    expires_in_seconds: int | None = None,
    external_elicitation_id: str | None = None,
    metadata: list[tuple[str, str]] | None = None,
) -> str:
    """Create an elicitation request (FORM or URL mode)."""
    try:
        mode_upper = mode.upper()
        if mode_upper not in ("FORM", "URL"):
            return f"elicit: invalid mode '{mode}' (expected FORM or URL)"

        parsed_schema = _parse_json_arg(schema, field="--schema")
        if mode_upper == "FORM" and parsed_schema is None:
            return "elicit: --schema is required when --mode FORM"
        if mode_upper == "URL" and not url:
            return "elicit: --url is required when --mode URL"

        params = _build_create_params(
            mode=mode_upper,
            message=message,
            tool_name=tool_name,
            schema=parsed_schema,
            url=url,
            chat_id=chat_id,
            message_id=message_id,
            expires_in_seconds=expires_in_seconds,
            external_elicitation_id=external_elicitation_id,
            metadata=_parse_metadata_pairs(metadata),
        )

        elicitation = unique_sdk.Elicitation.create_elicitation(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )
        return (
            f"Created elicitation {elicitation.get('id', '?')}\n\n"
            f"{format_elicitation(elicitation)}"
        )
    except (ValueError, unique_sdk.APIError) as exc:
        return f"elicit: {exc}"


def cmd_elicit_pending(state: ShellState) -> str:
    """List all pending elicitation requests for the current user."""
    try:
        response = unique_sdk.Elicitation.get_pending_elicitations(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
        )
        return format_pending_elicitations(response.get("elicitations", []))
    except unique_sdk.APIError as exc:
        return f"elicit: {exc}"


def cmd_elicit_get(state: ShellState, elicitation_id: str) -> str:
    """Fetch an elicitation by ID and show its details."""
    try:
        elicitation = unique_sdk.Elicitation.get_elicitation(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            elicitation_id=elicitation_id,
        )
        return format_elicitation(elicitation)
    except unique_sdk.APIError as exc:
        return f"elicit: {exc}"


def cmd_elicit_respond(
    state: ShellState,
    elicitation_id: str,
    *,
    action: str,
    content: str | None = None,
) -> str:
    """Respond to an elicitation on behalf of the user.

    Typically the *user* responds via the Unique UI; this command is primarily
    useful for scripted workflows, tests, or declining / cancelling requests
    on their behalf.
    """
    try:
        action_upper = action.upper()
        if action_upper not in ("ACCEPT", "DECLINE", "CANCEL"):
            return (
                f"elicit: invalid action '{action}' "
                "(expected ACCEPT, DECLINE, or CANCEL)"
            )

        parsed_content = _parse_json_arg(content, field="--content")
        if action_upper == "ACCEPT" and parsed_content is None:
            return "elicit: --content (JSON object) is required for ACCEPT"

        params: dict[str, Any] = {
            "elicitationId": elicitation_id,
            "action": action_upper,
        }
        if parsed_content is not None:
            params["content"] = parsed_content

        result = unique_sdk.Elicitation.respond_to_elicitation(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )
        return format_elicitation_response(result, elicitation_id, action_upper)
    except (ValueError, unique_sdk.APIError) as exc:
        return f"elicit: {exc}"


def cmd_elicit_wait(
    state: ShellState,
    elicitation_id: str,
    *,
    timeout: int = DEFAULT_WAIT_TIMEOUT_SECONDS,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> str:
    """Block until an elicitation transitions to a terminal state.

    Polls ``get_elicitation`` at ``poll_interval`` intervals and returns the
    formatted elicitation once its ``status`` is RESPONDED / DECLINED /
    CANCELLED / EXPIRED / COMPLETED, or when ``timeout`` seconds elapse.
    """
    try:
        deadline = time.monotonic() + max(1, timeout)
        last: dict[str, Any] | None = None
        while True:
            elicitation = unique_sdk.Elicitation.get_elicitation(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                elicitation_id=elicitation_id,
            )
            last = dict(elicitation)
            status = str(elicitation.get("status", "")).upper()
            if status in TERMINAL_STATUSES:
                return format_elicitation(elicitation)
            if time.monotonic() >= deadline:
                return (
                    f"elicit: timed out after {timeout}s waiting for "
                    f"{elicitation_id} (last status: {status or 'UNKNOWN'})\n\n"
                    f"{format_elicitation(last)}"
                )
            time.sleep(poll_interval)
    except unique_sdk.APIError as exc:
        return f"elicit: {exc}"


def cmd_elicit_ask(
    state: ShellState,
    *,
    message: str,
    tool_name: str = "agent_question",
    schema: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
    expires_in_seconds: int | None = None,
    timeout: int = DEFAULT_WAIT_TIMEOUT_SECONDS,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    metadata: list[tuple[str, str]] | None = None,
) -> str:
    """Create a FORM elicitation and wait for the user's reply.

    When no ``--schema`` is passed, a minimal single-field form asking for a
    free-text ``answer`` is used. This is the preferred entry point when an
    agent needs to ask the user a clarifying question.
    """
    try:
        parsed_schema = _parse_json_arg(schema, field="--schema")
        if parsed_schema is None:
            parsed_schema = {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Free-text answer to the question.",
                    },
                },
                "required": ["answer"],
            }

        params = _build_create_params(
            mode="FORM",
            message=message,
            tool_name=tool_name,
            schema=parsed_schema,
            url=None,
            chat_id=chat_id,
            message_id=message_id,
            expires_in_seconds=expires_in_seconds,
            external_elicitation_id=None,
            metadata=_parse_metadata_pairs(metadata),
        )

        elicitation = unique_sdk.Elicitation.create_elicitation(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )
        elicitation_id = elicitation.get("id")
        if not elicitation_id:
            return "elicit: platform did not return an elicitation id"

        return cmd_elicit_wait(
            state,
            elicitation_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    except (ValueError, unique_sdk.APIError) as exc:
        return f"elicit: {exc}"
