from typing import Unpack

from unique_toolkit.agentic.loop_runner._iteration_handler_utils import (
    run_forced_tools_iteration,
)
from unique_toolkit.agentic.loop_runner.base import _LoopIterationRunnerKwargs
from unique_toolkit.agentic.loop_runner.runners.basic import (
    BasicLoopIterationRunner,
)
from unique_toolkit.chat.functions import LanguageModelStreamResponse


class MistralLoopIterationRunner(BasicLoopIterationRunner):
    """Runner for Mistral models.

    Mistral doesn't support named tool_choice (``{"type": "function", ...}``).
    This runner overrides forced-tool handling to send ``"any"`` instead,
    which forces the model to call a tool. Since each forced iteration already
    restricts the tools list to a single tool, ``"any"`` effectively forces
    the correct one.
    """

    async def _handle_forced_tools(
        self,
        **kwargs: Unpack[_LoopIterationRunnerKwargs],
    ) -> LanguageModelStreamResponse:
        return await run_forced_tools_iteration(
            loop_runner_kwargs=kwargs,
            tool_choice_override="any",
        )
