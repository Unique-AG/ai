from typing import Literal, overload

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


@overload
def build_loop_iteration_runner(
    *,
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    chat_service: ChatService,
    use_responses_api: Literal[True],
    openai_client: AsyncOpenAI,
    llm_service: LanguageModelService | None = ...,
) -> ResponsesLoopIterationRunner: ...


@overload
def build_loop_iteration_runner(
    *,
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    chat_service: ChatService,
    llm_service: LanguageModelService,
    use_responses_api: Literal[False] = False,
    openai_client: AsyncOpenAI | None = ...,
) -> LoopIterationRunner: ...


def build_loop_iteration_runner(
    *,
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    chat_service: ChatService,
    use_responses_api: bool = False,
    llm_service: LanguageModelService | None = None,
    openai_client: AsyncOpenAI | None = None,
) -> LoopIterationRunner | ResponsesLoopIterationRunner:
    if use_responses_api:
        responses_runner: ResponsesLoopIterationRunner = (
            ResponsesBasicLoopIterationRunner(
                config=BasicLoopIterationRunnerConfig(
                    max_loop_iterations=config.agent.max_loop_iterations
                )
            )
        )
        if config.agent.experimental.loop_configuration.planning_config is not None:
            if openai_client is None:
                raise ValueError("openai_client is required when use_responses_api is True")

            responses_runner = ResponsesPlanningMiddleware(
                loop_runner=responses_runner,
                config=config.agent.experimental.loop_configuration.planning_config,
                openai_client=openai_client,
                history_manager=history_manager,
            )
        return responses_runner

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
        if llm_service is None:
            raise ValueError("llm_service is required when use_responses_api is False")

        runner = PlanningMiddleware(
            loop_runner=runner,
            config=config.agent.experimental.loop_configuration.planning_config,
            history_manager=history_manager,
            llm_service=llm_service,
        )

    return runner
