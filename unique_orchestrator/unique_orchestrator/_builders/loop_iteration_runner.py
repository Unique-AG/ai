from openai import AsyncOpenAI
from unique_toolkit import LanguageModelService
from unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
)
from unique_toolkit.agentic.loop_runner import (
    BasicLoopIterationRunner,
    BasicLoopIterationRunnerConfig,
    LoopIterationRunner,
    MistralLoopIterationRunner,
    PlanningMiddleware,
    QwenLoopIterationRunner,
    ResponsesBasicLoopIterationRunner,
    ResponsesLoopIterationRunner,
    ResponsesPlanningMiddleware,
)
from unique_toolkit.chat.service import ChatService

from unique_orchestrator.config import UniqueAIConfig, get_model_family


def build_responses_loop_iteration_runner(
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    openai_client: AsyncOpenAI,
) -> ResponsesLoopIterationRunner:
    runner = ResponsesBasicLoopIterationRunner(
        config=BasicLoopIterationRunnerConfig(
            max_loop_iterations=config.agent.max_loop_iterations
        )
    )

    if config.agent.experimental.loop_configuration.planning_config is not None:
        runner = ResponsesPlanningMiddleware(
            loop_runner=runner,
            config=config.agent.experimental.loop_configuration.planning_config,
            openai_client=openai_client,
            history_manager=history_manager,
        )

    return runner


def build_loop_iteration_runner(
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    chat_service: ChatService,
    llm_service: LanguageModelService,
) -> LoopIterationRunner:
    base_config = BasicLoopIterationRunnerConfig(
        max_loop_iterations=config.agent.max_loop_iterations
    )
    family = get_model_family(str(config.space.language_model))

    if family == "qwen":
        qwen_cfg = config.agent.experimental.loop_configuration.model_specific.qwen
        runner: LoopIterationRunner = QwenLoopIterationRunner(
            config=BasicLoopIterationRunnerConfig(
                max_loop_iterations=qwen_cfg.max_loop_iterations
            ),
            forced_tool_call_instruction=qwen_cfg.forced_tool_call_instruction,
            last_iteration_instruction=qwen_cfg.last_iteration_instruction,
            chat_service=chat_service,
        )
    elif family == "mistral":
        runner = MistralLoopIterationRunner(config=base_config)
    else:
        runner = BasicLoopIterationRunner(config=base_config)

    if config.agent.experimental.loop_configuration.planning_config is not None:
        runner = PlanningMiddleware(
            loop_runner=runner,
            config=config.agent.experimental.loop_configuration.planning_config,
            history_manager=history_manager,
            llm_service=llm_service,
        )

    return runner
