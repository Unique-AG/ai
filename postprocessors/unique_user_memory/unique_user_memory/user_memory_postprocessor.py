from collections.abc import Awaitable, Callable
from logging import Logger

from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model.default_language_model import (
    DEFAULT_LANGUAGE_MODEL,
)
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory import (
    UserMemoryState,
    consolidate_user_memory,
    upload_user_memory,
)
from unique_user_memory.user_memory_message_log import UserMemoryMessageLogger


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
        chat_service: ChatService,
        message_step_logger: MessageStepLogger | None = None,
        message_logger: UserMemoryMessageLogger | None = None,
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
        self._new_memory: str | None = None
        self._chat_service: ChatService = chat_service
        self._pending_load_invocation_stats = list(state.load_invocation_stats)
        self._invocation_stats: list[LanguageModelInvocationStats] = []
        if message_logger is not None:
            self._message_logger = message_logger
        elif message_step_logger is not None:
            self._message_logger = UserMemoryMessageLogger(
                message_step_logger,
                logger=logger,
            )
        else:
            self._message_logger = UserMemoryMessageLogger(
                MessageStepLogger(chat_service),
                logger=logger,
            )

    @property
    def invocation_stats(self) -> list[LanguageModelInvocationStats]:
        return list(self._invocation_stats)

    def take_pending_invocation_stats(self) -> list[LanguageModelInvocationStats]:
        """Pop load-time condense stats not yet reported.

        `UniqueAI` calls this unconditionally at the start of every turn so a
        turn that exits before `run()` (cancellation, empty response, a
        control-taking tool) still reports the tokens spent condensing the
        loaded profile. If `run()` does execute, it drains the same pending
        list itself, so whichever of the two runs first "wins" and the other
        sees an empty list -- the tokens are never double-counted or lost.
        """
        stats, self._pending_load_invocation_stats = (
            self._pending_load_invocation_stats,
            [],
        )
        return stats

    async def run(self, loop_response: LanguageModelStreamResponse) -> bool:
        """Consolidate and upload user memory for this turn.

        Returns True if the memory profile changed and was uploaded, False
        otherwise (no user/company, NOOP consolidation, or failed upload).
        """
        self._invocation_stats = self.take_pending_invocation_stats()
        self._logger.info("[user-memory] running postprocessor")
        user_id = self._event.user_id
        company_id = self._event.company_id
        if not user_id or not company_id:
            return False

        content_id = self._state.content_id

        async def _on_update_start() -> None:
            await self._message_logger.log_updating_start(content_id=content_id)

        async def _on_update_end() -> None:
            await self._message_logger.log_updating_complete(content_id=content_id)

        on_update_start: Callable[[], Awaitable[None]] = _on_update_start
        on_update_end: Callable[[], Awaitable[None]] = _on_update_end

        self._new_memory = await consolidate_user_memory(
            current_memory=self._state.text,
            user_id=user_id,
            user_message=self._event.payload.user_message.text or "",
            assistant_message=loop_response.message.text or "",
            config=self._config,
            language_model=self._language_model,
            event=self._event,
            logger=self._logger,
            on_update_start=on_update_start,
            on_update_end=on_update_end,
            invocation_stats=self._invocation_stats,
        )

        if self._new_memory == self._state.text:
            self._logger.debug("[user-memory] consolidation NOOP - skipping upload")
            return False

        uploaded_content_id = await upload_user_memory(
            scope_id=self._state.scope_id,
            content=self._new_memory,
            user_id=user_id,
            company_id=company_id,
            logger=self._logger,
        )
        if not uploaded_content_id:
            self._logger.warning("[user-memory] memory update was not uploaded")
            return False

        # Prefer the freshly uploaded id so the review pill works on first write.
        await self._message_logger.log_updating_complete(
            content_id=uploaded_content_id or content_id
        )
        self._logger.info("[user-memory] memory updated and uploaded successfully")
        return True

    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        return False

    async def remove_from_text(self, text: str) -> str:
        return text
