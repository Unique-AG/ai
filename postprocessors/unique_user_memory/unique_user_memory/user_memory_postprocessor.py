from collections.abc import Awaitable, Callable
from logging import Logger

from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentReference
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
    noop_update_callback,
    upload_user_memory,
)

# Transient marker appended to the assistant message while the (slow) memory
# rewrite runs; removed again once consolidation finishes.
_UPDATING_NOTICE = "\n\n---\n\n🧠 _Updating context memory…_"


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

        on_update_start: Callable[[], Awaitable[None]] = noop_update_callback
        on_update_end: Callable[[], Awaitable[None]] = noop_update_callback
        if self._config.updating_notice_enabled:
            original_text = loop_response.message.text or ""
            message_id = loop_response.message.id
            references = loop_response.message.references

            async def _on_update_start() -> None:
                await self._set_message_content(
                    content=original_text + _UPDATING_NOTICE,
                    message_id=message_id,
                    references=references,
                    action="show updating notice",
                )

            async def _on_update_end() -> None:
                await self._set_message_content(
                    content=original_text,
                    message_id=message_id,
                    references=references,
                    action="remove updating notice",
                )

            on_update_start = _on_update_start
            on_update_end = _on_update_end

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

        uploaded = await upload_user_memory(
            scope_id=self._state.scope_id,
            content=self._new_memory,
            user_id=user_id,
            company_id=company_id,
            logger=self._logger,
        )
        if not uploaded:
            self._logger.warning("[user-memory] memory update was not uploaded")
            return False

        self._logger.info("[user-memory] memory updated and uploaded successfully")
        return True

    async def _set_message_content(
        self,
        *,
        content: str,
        message_id: str | None,
        references: list[ContentReference] | None,
        action: str,
    ) -> None:
        try:
            await self._chat_service.modify_assistant_message_async(
                content=content,
                message_id=message_id,
                references=references,
            )
        except Exception as exc:
            self._logger.warning(
                "[user-memory] failed to %s: [%s] %s",
                action,
                type(exc).__name__,
                exc,
            )

    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        return False

    async def remove_from_text(self, text: str) -> str:
        return text
