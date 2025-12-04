import logging
from typing import Unpack, override

from pydantic import BaseModel

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.loop_runner._stream_handler_utils import stream_response
from unique_toolkit.agentic.loop_runner.base import LoopRunner, _LoopRunnerKwargs
from unique_toolkit.chat.functions import LanguageModelStreamResponse
from unique_toolkit.protocols.support import (
    ResponsesLanguageModelStreamResponse,
)

logger = logging.getLogger(__name__)


class BasicLoopRunnerConfig(BaseModel):
    model_config = get_configuration_dict()
    max_loop_iterations: int


class BasicLoopRunner(LoopRunner):
    def __init__(self, config: BasicLoopRunnerConfig) -> None:
        self._config = config

    async def _handle_last_iteration(
        self, **kwargs: Unpack[_LoopRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        logger.info(
            "Reached last iteration, removing tools and producing final response"
        )

        return await stream_response(
            loop_runner_kwargs=kwargs,
            tools=None,
        )

    async def _handle_normal_iteration(
        self, **kwargs: Unpack[_LoopRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        logger.info("Running loop iteration %d", kwargs["iteration_index"])

        return await stream_response(loop_runner_kwargs=kwargs)

    async def _handle_forced_tools_iteration(
        self,
        **kwargs: Unpack[_LoopRunnerKwargs],
    ) -> LanguageModelStreamResponse:
        assert "tool_choices" in kwargs

        tool_choices = kwargs["tool_choices"]
        logger.info("Forcing tools calls: %s", tool_choices)

        responses: list[LanguageModelStreamResponse] = []

        for opt in tool_choices:
            responses.append(
                await stream_response(
                    loop_runner_kwargs=kwargs,
                    tool_choice=opt,
                )
            )

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
        **kwargs: Unpack[_LoopRunnerKwargs],
    ) -> LanguageModelStreamResponse | ResponsesLanguageModelStreamResponse:
        tool_choices = kwargs.get("tool_choices", [])
        iteration_index = kwargs["iteration_index"]

        if len(tool_choices) > 0 and iteration_index == 0:
            return await self._handle_forced_tools_iteration(**kwargs)
        elif iteration_index == self._config.max_loop_iterations - 1:
            return await self._handle_last_iteration(**kwargs)
        else:
            return await self._handle_normal_iteration(**kwargs)
