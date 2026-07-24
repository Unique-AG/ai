"""MessageLog Steps for user-memory load and update."""

from logging import Logger, getLogger

from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.content.schemas import ContentReference

_LOGGER = getLogger(__name__)

_LOADING_HEADER = "Loading context memory"
_UPDATING_HEADER = "Updating your memory"
_CONTEXT_MEMORY_PILL = "Context memory"
_REVIEW_MEMORY_PILL = "Review your context memory"


def _memory_reference(*, name: str, content_id: str) -> ContentReference:
    return ContentReference(
        name=name,
        sequence_number=0,
        source="internal",
        source_id=content_id,
        url=f"unique://content/{content_id}",
    )


class UserMemoryMessageLogger:
    """Emits Steps for loading and updating the user's context memory file."""

    def __init__(
        self,
        message_step_logger: MessageStepLogger,
        *,
        logger: Logger | None = None,
    ) -> None:
        self._message_step_logger = message_step_logger
        self._logger = logger or _LOGGER
        self._loading_log: MessageLog | None = None
        self._updating_log: MessageLog | None = None

    async def log_loading_start(self) -> None:
        await self._safe_create_or_update(
            active_attr="_loading_log",
            header=_LOADING_HEADER,
            status=MessageLogStatus.RUNNING,
            references=[],
            action="start loading step",
        )

    async def log_loading_complete(self, *, content_id: str | None) -> None:
        # Attach the pill on the loading step itself (same pattern as update).
        # A separate MessageLog with empty text is dropped / invisible in the
        # chat Steps UI, so the link must ride on this COMPLETED entry.
        references = (
            [_memory_reference(name=_CONTEXT_MEMORY_PILL, content_id=content_id)]
            if content_id
            else []
        )
        await self._safe_create_or_update(
            active_attr="_loading_log",
            header=_LOADING_HEADER,
            status=MessageLogStatus.COMPLETED,
            references=references,
            action="complete loading step",
        )

    async def log_updating_start(self, *, content_id: str | None) -> None:
        references = (
            [_memory_reference(name=_REVIEW_MEMORY_PILL, content_id=content_id)]
            if content_id
            else []
        )
        await self._safe_create_or_update(
            active_attr="_updating_log",
            header=_UPDATING_HEADER,
            status=MessageLogStatus.RUNNING,
            references=references,
            action="start updating step",
        )

    async def log_updating_complete(self, *, content_id: str | None) -> None:
        references = (
            [_memory_reference(name=_REVIEW_MEMORY_PILL, content_id=content_id)]
            if content_id
            else []
        )
        await self._safe_create_or_update(
            active_attr="_updating_log",
            header=_UPDATING_HEADER,
            status=MessageLogStatus.COMPLETED,
            references=references,
            action="complete updating step",
        )

    async def _safe_create_or_update(
        self,
        *,
        active_attr: str,
        header: str,
        status: MessageLogStatus,
        references: list[ContentReference],
        action: str,
    ) -> None:
        try:
            active = getattr(self, active_attr)
            updated = (
                await self._message_step_logger.create_or_update_message_log_async(
                    active_message_log=active,
                    header=header,
                    status=status,
                    references=references,
                )
            )
            if updated is not None:
                setattr(self, active_attr, updated)
        except Exception as exc:
            self._logger.warning(
                "[user-memory] failed to %s: [%s] %s",
                action,
                type(exc).__name__,
                exc,
            )
