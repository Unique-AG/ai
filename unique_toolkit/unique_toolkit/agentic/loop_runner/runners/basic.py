import logging
from typing import Unpack, override

from pydantic import BaseModel

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.loop_runner._stream_handler_utils import stream_response
from unique_toolkit.agentic.loop_runner.base import (
    LoopIterationRunner,
    _LoopIterationRunnerKwargs,
)
from unique_toolkit.chat.functions import LanguageModelStreamResponse
from unique_toolkit.protocols.support import (
    ResponsesLanguageModelStreamResponse,
)

_LOGGER = logging.getLogger(__name__)


class BasicLoopIterationRunnerConfig(BaseModel):
    model_config = get_configuration_dict()
    max_loop_iterations: int


class BasicLoopIterationRunner(LoopIterationRunner):
    def __init__(self, config: BasicLoopIterationRunnerConfig) -> None:
        self._config = config

    async def _handle_last_iteration(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        _LOGGER.info(
            "Reached last iteration, removing tools and producing final response"
        )

        return await stream_response(
            loop_runner_kwargs=kwargs,
            tools=None,
        )

    async def _handle_normal_iteration(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        _LOGGER.info("Running loop iteration %d", kwargs["iteration_index"])

        return await stream_response(loop_runner_kwargs=kwargs)

    async def _handle_forced_tools_iteration(
        self,
        **kwargs: Unpack[_LoopIterationRunnerKwargs],
    ) -> LanguageModelStreamResponse:
        assert "tool_choices" in kwargs

        tool_choices = kwargs["tool_choices"]
        _LOGGER.info("Forcing tools calls: %s", tool_choices)

        responses: list[LanguageModelStreamResponse] = []

        available_tools = {t.name: t for t in kwargs.get("tools") or []}

        for opt in tool_choices:
            func_name = opt.get("function", {}).get("name")
            limited_tool = available_tools.get(func_name) if func_name else None
            stream_kwargs = {"loop_runner_kwargs": kwargs, "tool_choice": opt}
            if limited_tool:
                stream_kwargs["tools"] = [limited_tool]
            responses.append(await stream_response(**stream_kwargs))

        # Merge responses and refs:
        tool_calls = []
        references = []
        for r in responses:
            if r.tool_calls:
                tool_calls.extend(r.tool_calls)
            references.extend(r.message.references)

        response = responses[0]
        response.tool_calls = tool_calls if len(tool_calls) > 0 else None
        response.message.references = references

        return response

    @override
    async def __call__(
        self,
        **kwargs: Unpack[_LoopIterationRunnerKwargs],
    ) -> LanguageModelStreamResponse | ResponsesLanguageModelStreamResponse:
        tool_choices = kwargs.get("tool_choices", [])
        iteration_index = kwargs["iteration_index"]

        if len(tool_choices) > 0 and iteration_index == 0:
            return await self._handle_forced_tools_iteration(**kwargs)
        elif iteration_index == self._config.max_loop_iterations - 1:
            return await self._handle_last_iteration(**kwargs)
        else:
            return await self._handle_normal_iteration(**kwargs)
