import json
import logging
from typing import Any, Unpack

from openai import AsyncOpenAI
from openai.types.responses import (
    Response,
    ResponseFunctionToolCall,
    ResponseInputItemParam,
    ToolParam,
)
from openai.types.responses.function_tool_param import FunctionToolParam
from pydantic import BaseModel, Field

from unique_toolkit import LanguageModelService, LanguageModelToolDescription
from unique_toolkit._common.execution import failsafe_async
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.loop_runner.base import (
    LoopIterationRunner,
    ResponsesLoopIterationRunner,
    _LoopIterationRunnerKwargs,
    _ResponsesLoopIterationRunnerKwargs,
)
from unique_toolkit.agentic.loop_runner.middleware.planning.schema import (
    PlanningSchemaConfig,
    get_planning_schema,
)
from unique_toolkit.chat.responses_api import convert_messages_to_openai
from unique_toolkit.chat.service import LanguageModelStreamResponse
from unique_toolkit.language_model import (
    LanguageModelAssistantMessage,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    ResponsesLanguageModelStreamResponse,
)

_LOGGER = logging.getLogger(__name__)


_PLAN_TOOL_NAME = "plan"
_PLAN_TOOL_DESCRIPTION = (
    "Record the plan for the next step. Call this tool exactly once."
)

# Kwargs from _ResponsesLoopIterationRunnerKwargs that make sense to forward to
# the planning `responses.create` call. We deliberately exclude anything that
# conflicts with the forced-tool-call setup (`tools`, `tool_choices`, `text`,
# `parallel_tool_calls`) and anything that is a loop-runner control knob rather
# than a model option.
_FORWARDABLE_RESPONSES_OPTIONS: frozenset[str] = frozenset(
    {
        "temperature",
        "top_p",
        "reasoning",
        "max_output_tokens",
        "metadata",
        "include",
        "instructions",
    }
)


def _get_first_tool_call_arguments(response: Response) -> str | None:
    """
    Extract the arguments of the first ``function_call`` output item.

    Using a forced tool call (``tool_choice={"type": "function", ...}``) avoids
    the duplicate-output issue the Responses API exhibits with
    ``text.format=json_schema`` structured output.
    """
    if len(response.output) > 1:
        _LOGGER.warning(
            "Model returned %i outputs, keeping only the first one",
            len(response.output),
        )

    for item in response.output:
        if isinstance(item, ResponseFunctionToolCall) and item.arguments:
            return item.arguments
    return None


class PlanningConfig(BaseModel):
    model_config = get_configuration_dict()

    planning_schema_config: PlanningSchemaConfig = PlanningSchemaConfig()
    ignored_options: list[str] = Field(
        default=["parallel_tool_calls"],
        description="A list of options to ignore when calling the LLM for the planning step.",
    )


class PlanningMiddleware(LoopIterationRunner):
    def __init__(
        self,
        *,
        loop_runner: LoopIterationRunner,
        config: PlanningConfig,
        llm_service: LanguageModelService,
        history_manager: HistoryManager | None = None,
    ) -> None:
        self._config = config
        self._loop_runner = loop_runner
        self._history_manager = history_manager
        self._llm_service = llm_service

    @failsafe_async(failure_return_value=None, logger=_LOGGER)
    async def _run_plan_step(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelAssistantMessage | None:
        planning_schema = get_planning_schema(self._config.planning_schema_config)

        other_options = {
            k: v
            for k, v in kwargs.get("other_options", {}).items()
            if k not in self._config.ignored_options
        }
        response = await self._llm_service.complete_async(
            messages=kwargs["messages"],
            model_name=kwargs["model"].name,
            structured_output_model=planning_schema,
            other_options=other_options,
        )

        if response.choices[0].message.parsed is None:
            _LOGGER.info("Error parsing planning response")
            return None

        return LanguageModelAssistantMessage(
            content=json.dumps(response.choices[0].message.parsed)
        )

    async def __call__(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        assistant_message = await self._run_plan_step(**kwargs)

        if assistant_message is None:
            _LOGGER.info(
                "Error executing planning step, proceeding without planning step"
            )
            return await self._loop_runner(**kwargs)

        if self._history_manager is not None:
            self._history_manager.add_assistant_message(assistant_message)

        kwargs["messages"] = (
            kwargs["messages"].builder().append(assistant_message).build()
        )
        return await self._loop_runner(**kwargs)


class ResponsesPlanningMiddleware(ResponsesLoopIterationRunner):
    def __init__(
        self,
        *,
        loop_runner: ResponsesLoopIterationRunner,
        config: PlanningConfig,
        openai_client: AsyncOpenAI,
        history_manager: HistoryManager | None = None,
    ) -> None:
        self._config = config
        self._loop_runner = loop_runner
        self._history_manager = history_manager
        self._openai_client = openai_client

    def _build_forwarded_options(
        self, kwargs: _ResponsesLoopIterationRunnerKwargs
    ) -> dict[str, Any]:
        ignored = set(self._config.ignored_options)
        forwarded: dict[str, Any] = {
            k: v
            for k, v in kwargs.items()
            if k in _FORWARDABLE_RESPONSES_OPTIONS and k not in ignored
        }

        other_options = kwargs.get("other_options") or {}
        forwarded.update({k: v for k, v in other_options.items() if k not in ignored})
        return forwarded

    def _build_tools(
        self, kwargs: _ResponsesLoopIterationRunnerKwargs
    ) -> list[FunctionToolParam | ToolParam]:
        """
        Build the tool list sent to the planning call: the forced ``plan`` tool
        plus the loop runner's regular tools (converted to Responses API shape).

        Passing the regular tools gives the model the information it needs to
        reason about *which* tool to call next, even though ``tool_choice``
        pins the actual call to ``plan``.
        """
        planning_schema = get_planning_schema(self._config.planning_schema_config)
        plan_tool = FunctionToolParam(
            type="function",
            name=_PLAN_TOOL_NAME,
            description=_PLAN_TOOL_DESCRIPTION,
            parameters=planning_schema,
            strict=False,
        )

        extra_tools: list[FunctionToolParam | ToolParam] = []
        for tool in kwargs.get("tools") or []:
            if isinstance(tool, LanguageModelToolDescription):
                converted = tool.to_openai(mode="responses")
            else:
                converted = tool
            if converted.get("name") == _PLAN_TOOL_NAME:
                continue
            extra_tools.append(converted)

        return [plan_tool, *extra_tools]

    @failsafe_async(failure_return_value=None, logger=_LOGGER)
    async def _run_plan_step(
        self,
        openai_messages: str | list[ResponseInputItemParam],
        model_name: str,
        tools: list[FunctionToolParam | ToolParam],
        forwarded_options: dict[str, Any],
    ) -> str | None:
        response = await self._openai_client.responses.create(
            model=model_name,
            input=openai_messages,
            tools=tools,
            tool_choice={"type": "function", "name": _PLAN_TOOL_NAME},
            parallel_tool_calls=False,
            **forwarded_options,
        )

        output_text = _get_first_tool_call_arguments(response)
        if not output_text:
            _LOGGER.info("Empty planning response")
            return None

        return output_text

    async def __call__(
        self, **kwargs: Unpack[_ResponsesLoopIterationRunnerKwargs]
    ) -> ResponsesLanguageModelStreamResponse:
        openai_messages = convert_messages_to_openai(kwargs["messages"])

        output_text = await self._run_plan_step(
            openai_messages=openai_messages,
            model_name=kwargs["model"].name,
            tools=self._build_tools(kwargs),
            forwarded_options=self._build_forwarded_options(kwargs),
        )

        if output_text is None:
            _LOGGER.info(
                "Error executing planning step, proceeding without planning step"
            )
            return await self._loop_runner(**kwargs)

        assistant_message = LanguageModelAssistantMessage(content=output_text)

        if self._history_manager is not None:
            self._history_manager.add_assistant_message(assistant_message)

        if isinstance(kwargs["messages"], str):
            kwargs["messages"] = [
                LanguageModelUserMessage(content=kwargs["messages"]),
                assistant_message,
            ]
        elif isinstance(kwargs["messages"], LanguageModelMessages):
            kwargs["messages"] = (
                kwargs["messages"].builder().append(assistant_message).build()
            )
        else:
            kwargs["messages"] = list(kwargs["messages"]) + [assistant_message]

        return await self._loop_runner(**kwargs)
