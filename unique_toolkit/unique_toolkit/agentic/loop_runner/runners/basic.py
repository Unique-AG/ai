import logging
from typing import Unpack, override

from pydantic import BaseModel

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.loop_runner._iteration_handler_utils import (
    handle_forced_tools_iteration,
    handle_last_iteration,
    handle_normal_iteration,
)
from unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils import (
    handle_responses_forced_tools_iteration,
    handle_responses_last_iteration,
    handle_responses_normal_iteration,
)
from unique_toolkit.agentic.loop_runner.base import (
    LoopIterationRunner,
    ResponsesLoopIterationRunner,
    _LoopIterationRunnerKwargs,
    _ResponsesLoopIterationRunnerKwargs,
)
from unique_toolkit.chat.functions import LanguageModelStreamResponse
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

_LOGGER = logging.getLogger(__name__)


class BasicLoopIterationRunnerConfig(BaseModel):
    model_config = get_configuration_dict()
    max_loop_iterations: int


class BasicLoopIterationRunner(LoopIterationRunner):
    def __init__(self, config: BasicLoopIterationRunnerConfig) -> None:
        self._config = config

    @override
    async def __call__(
        self,
        **kwargs: Unpack[_LoopIterationRunnerKwargs],
    ) -> LanguageModelStreamResponse:
        tool_choices = kwargs.get("tool_choices", [])
        iteration_index = kwargs["iteration_index"]

        if len(tool_choices) > 0 and iteration_index == 0:
            return await handle_forced_tools_iteration(**kwargs)
        elif iteration_index == self._config.max_loop_iterations - 1:
            return await handle_last_iteration(**kwargs)
        else:
            return await handle_normal_iteration(**kwargs)


class ResponsesBasicLoopIterationRunner(ResponsesLoopIterationRunner):
    def __init__(self, config: BasicLoopIterationRunnerConfig) -> None:
        self._config = config

    @override
    async def __call__(
        self,
        **kwargs: Unpack[_ResponsesLoopIterationRunnerKwargs],
    ) -> ResponsesLanguageModelStreamResponse:
        tool_choices = kwargs.get("tool_choices", [])
        iteration_index = kwargs["iteration_index"]

        if len(tool_choices) > 0 and iteration_index == 0:
            return await handle_responses_forced_tools_iteration(**kwargs)
        elif iteration_index == self._config.max_loop_iterations - 1:
            return await handle_responses_last_iteration(**kwargs)
        else:
            return await handle_responses_normal_iteration(**kwargs)
