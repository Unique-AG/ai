from logging import Logger

from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.default_language_model import (
    DEFAULT_LANGUAGE_MODEL,
)
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory import (
    UserMemoryState,
    build_user_memory_references,
    consolidate_user_memory,
    upload_user_memory,
)


class UserMemoryPostprocessor(Postprocessor):
    def __init__(
        self,
        *,
        config: UserMemoryConfig,
        language_model: LanguageModelInfo = LanguageModelInfo.from_name(
            DEFAULT_LANGUAGE_MODEL
        ),
        event: ChatEvent,
        state: UserMemoryState,
        logger: Logger,
        message_step_logger: MessageStepLogger | None = None,
    ) -> None:
        super().__init__(name="UserMemoryPostprocessor")
        self._config = config
        self._language_model = (
            language_model
            if config.use_orchestrator_language_model
            else config.language_model
        )
        self._event = event
        self._state = state
        self._logger = logger
        self._message_step_logger = message_step_logger
        self._new_memory: str | None = None

    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        self._logger.info("[user-memory] running postprocessor")
        user_id = self._event.user_id
        company_id = self._event.company_id
        if not user_id or not company_id:
            return

        self._new_memory = await consolidate_user_memory(
            current_memory=self._state.text,
            user_id=user_id,
            user_message=self._event.payload.user_message.text or "",
            assistant_message=loop_response.message.text or "",
            config=self._config,
            language_model=self._language_model,
            event=self._event,
            logger=self._logger,
        )

        if self._new_memory == self._state.text:
            self._logger.debug("[user-memory] consolidation NOOP - skipping upload")
            return

        uploaded = await upload_user_memory(
            scope_id=self._state.scope_id,
            content=self._new_memory,
            user_id=user_id,
            company_id=company_id,
            logger=self._logger,
        )
        if not uploaded:
            self._logger.warning("[user-memory] memory update was not uploaded")
            return

        self._logger.info("[user-memory] memory updated and uploaded successfully")

        if self._message_step_logger is not None:
            self._message_step_logger.create_message_log_entry(
                text="**User Memory Updated**",
                references=build_user_memory_references(self._state.content_id),
            )

    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        return False

    async def remove_from_text(self, text: str) -> str:
        return text
