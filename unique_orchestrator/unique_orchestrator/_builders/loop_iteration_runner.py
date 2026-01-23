from typing import Literal, overload

from unique_toolkit import LanguageModelService
from unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
)
from unique_toolkit.agentic.loop_runner import (
    BasicLoopIterationRunner,
    BasicLoopIterationRunnerConfig,
    LoopIterationRunner,
    PlanningMiddleware,
    QwenLoopIterationRunner,
    ResponsesBasicLoopIterationRunner,
    ResponsesLoopIterationRunner,
    is_qwen_model,
)
from unique_toolkit.chat.service import ChatService

from unique_orchestrator.config import UniqueAIConfig


@overload
def build_loop_iteration_runner(
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    llm_service: LanguageModelService,
    chat_service: ChatService,
    use_responses_api: Literal[False],
) -> LoopIterationRunner: ...


@overload
def build_loop_iteration_runner(
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    llm_service: LanguageModelService,
    chat_service: ChatService,
    use_responses_api: Literal[True],
) -> ResponsesLoopIterationRunner: ...


def build_loop_iteration_runner(
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    llm_service: LanguageModelService,
    chat_service: ChatService,
    use_responses_api: bool = False,
) -> LoopIterationRunner | ResponsesLoopIterationRunner:
    if use_responses_api:
        return ResponsesBasicLoopIterationRunner(
            config=BasicLoopIterationRunnerConfig(
                max_loop_iterations=config.agent.max_loop_iterations
            )
        )
    else:
        runner = BasicLoopIterationRunner(
            config=BasicLoopIterationRunnerConfig(
                max_loop_iterations=config.agent.max_loop_iterations
            )
        )

        if is_qwen_model(model=config.space.language_model):
            runner = QwenLoopIterationRunner(
                qwen_forced_tool_call_instruction=config.agent.experimental.loop_configuration.model_specific.qwen.forced_tool_call_instruction,
                qwen_last_iteration_instruction=config.agent.experimental.loop_configuration.model_specific.qwen.last_iteration_instruction,
                max_loop_iterations=config.agent.experimental.loop_configuration.model_specific.qwen.max_loop_iterations,
                chat_service=chat_service,
            )

        if config.agent.experimental.loop_configuration.planning_config is not None:
            runner = PlanningMiddleware(
                loop_runner=runner,
                config=config.agent.experimental.loop_configuration.planning_config,
                history_manager=history_manager,
                llm_service=llm_service,
            )

    return runner
