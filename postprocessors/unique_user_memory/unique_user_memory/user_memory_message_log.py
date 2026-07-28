"""MessageLog Steps for user-memory load and update."""

from logging import Logger, getLogger
from typing import Literal

from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.chat.schemas import (
    MessageLog,
    MessageLogDetails,
    MessageLogEvent,
    MessageLogStatus,
)

_LOGGER = getLogger(__name__)

_LOADING_HEADER = "Loading context memory"
_UPDATING_HEADER = "Updating your memory"
_CONTEXT_MEMORY_ENTRY_TEXT = "Context memory"
_REVIEW_MEMORY_ENTRY_TEXT = "Review your context memory"

# Typed MessageLog detail entry recognised by the chat frontend, which renders
# it as a badge that opens Settings → Context Memory. Frontends that don't know
# the type parse it as "Unknown" and render nothing, so emitting it is always
# safe regardless of deploy order.
USER_MEMORY_EVENT_TYPE: Literal["UserMemory"] = "UserMemory"


def _memory_settings_details(*, text: str) -> MessageLogDetails:
    return MessageLogDetails(
        data=[MessageLogEvent(type=USER_MEMORY_EVENT_TYPE, text=text)]
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
            details=None,
            action="start loading step",
        )

    async def log_loading_complete(self, *, with_settings_entry: bool = True) -> None:
        # Attach the settings entry on the loading step itself (same pattern
        # as update) — a separate MessageLog with empty text is dropped /
        # invisible in the chat Steps UI.
        details = (
            _memory_settings_details(text=_CONTEXT_MEMORY_ENTRY_TEXT)
            if with_settings_entry
            else None
        )
        await self._safe_create_or_update(
            active_attr="_loading_log",
            header=_LOADING_HEADER,
            status=MessageLogStatus.COMPLETED,
            details=details,
            action="complete loading step",
        )

    async def log_loading_failed(self) -> None:
        # Always close the RUNNING step when load raises; otherwise the chat
        # Steps UI leaves "Loading context memory" stuck for that turn.
        await self._safe_create_or_update(
            active_attr="_loading_log",
            header=_LOADING_HEADER,
            status=MessageLogStatus.FAILED,
            details=None,
            action="fail loading step",
        )

    async def log_updating_start(self) -> None:
        await self._safe_create_or_update(
            active_attr="_updating_log",
            header=_UPDATING_HEADER,
            status=MessageLogStatus.RUNNING,
            details=None,
            action="start updating step",
        )

    async def log_updating_complete(self, *, with_settings_entry: bool = False) -> None:
        # Review entry only after memory was actually written (caller sets
        # with_settings_entry=True post-upload). While consolidating / on
        # failed upload the step completes without it.
        details = (
            _memory_settings_details(text=_REVIEW_MEMORY_ENTRY_TEXT)
            if with_settings_entry
            else None
        )
        await self._safe_create_or_update(
            active_attr="_updating_log",
            header=_UPDATING_HEADER,
            status=MessageLogStatus.COMPLETED,
            details=details,
            action="complete updating step",
        )

    async def _safe_create_or_update(
        self,
        *,
        active_attr: str,
        header: str,
        status: MessageLogStatus,
        details: MessageLogDetails | None,
        action: str,
    ) -> None:
        try:
            active = getattr(self, active_attr)
            updated = (
                await self._message_step_logger.create_or_update_message_log_async(
                    active_message_log=active,
                    header=header,
                    status=status,
                    details=details,
                    references=[],
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
