from enum import StrEnum
from typing import Protocol

from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)


class ProgressState(StrEnum):
    STARTED = "started"
    RUNNING = "running"
    FAILED = "failed"
    FINISHED = "finished"


class ToolProgressReporterProtocol(Protocol):
    """Protocol defining the interface for tool progress reporters."""

    async def notify_from_tool_call(
        self,
        tool_call: LanguageModelFunction,
        name: str,
        message: str,
        state: ProgressState,
        references: list[ContentReference] | None = None,
    ) -> None:
        """Notify about a tool call execution status."""
        ...
