from logging import Logger

from pydantic import BaseModel

from unique_toolkit import ChatService, LanguageModelName, ShortTermMemoryService
from unique_toolkit._common.validators import LMI, LanguageModelInfo
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.debug_info_manager.debug_info_manager import DebugInfoManager
from unique_toolkit.evals.evaluation_manager import EvaluationManager
from unique_toolkit.history_manager.history_manager import (
    HistoryManager,
    HistoryManagerConfig,
)
from unique_toolkit.postprocessor.postprocessor_manager import PostprocessorManager
from unique_toolkit.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.short_term_memory.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.thinking_manager.thinking_manager import (
    ThinkingManager,
    ThinkingManagerConfig,
)
from unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter


class ManagerFactoryConfig:
    def __init__(
        self,
        thinking_manager_config: ThinkingManagerConfig | None = None,
        history_manager_config: HistoryManagerConfig | None = None,
    ):
        self._thinking_manager_config = thinking_manager_config
        self._history_manager_config = history_manager_config

    def get_thinking_manager_config(self) -> ThinkingManagerConfig:
        return self._thinking_manager_config or ThinkingManagerConfig()

    def get_history_manager_config(self) -> HistoryManagerConfig:
        return self._history_manager_config or HistoryManagerConfig()


class ManagerFactory:
    def __init__(
        self,
        event: ChatEvent,
        config: ManagerFactoryConfig,
        logger: Logger,
        language_model: LMI = LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_1120
        ),
    ):
        self._event = event
        self._config = config
        self._logger = logger
        self._language_model = language_model
        self._chat_service = ChatService(event=event)
        self._tool_progress_reporter = ToolProgressReporter(self._chat_service)
        self._short_term_memory_service = ShortTermMemoryService.from_event(event=event)

    def get_thinking_manager(self) -> ThinkingManager:
        return ThinkingManager(
            logger=self._logger,
            config=self._config.get_thinking_manager_config(),
            chat_service=self._chat_service,
            tool_progress_reporter=self._tool_progress_reporter,
        )

    def get_reference_manager(self) -> ReferenceManager:
        return ReferenceManager()

    def get_history_manager(self) -> HistoryManager:
        return HistoryManager(
            logger=self._logger,
            event=self._event,
            config=self._config.get_history_manager_config(),
            reference_manager=self.get_reference_manager(),
            language_model=self._language_model,
        )

    def get_postprocessor_manager(self) -> PostprocessorManager:
        return PostprocessorManager(
            logger=self._logger, chat_service=self._chat_service
        )

    def get_evaluation_manager(self) -> EvaluationManager:
        return EvaluationManager(
            logger=self._logger,
            chat_service=self._chat_service,
        )

    def get_persistent_short_term_memory_manager(
        self, schema: type[BaseModel]
    ) -> PersistentShortMemoryManager:
        return PersistentShortMemoryManager[schema](
            short_term_memory_service=self._short_term_memory_service,
            short_term_memory_schema=schema,
            short_term_memory_name=schema.__name__,
        )

    def get_debug_info_manager(self) -> DebugInfoManager:
        return DebugInfoManager()
