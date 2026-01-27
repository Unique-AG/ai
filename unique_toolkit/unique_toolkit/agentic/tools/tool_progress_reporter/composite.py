from typing import override

from unique_toolkit.agentic.tools.tool_progress_reporter import ProgressState
from unique_toolkit.agentic.tools.tool_progress_reporter.base import (
    ToolProgressReporterProtocol,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)


class CompositeToolProgressReporter(ToolProgressReporterProtocol):
    def __init__(self, reporters: list[ToolProgressReporterProtocol]) -> None:
        self._reporters = reporters

    @override
    async def notify_from_tool_call(
        self,
        tool_call: LanguageModelFunction,
        name: str,
        message: str,
        state: ProgressState,
        references: list[ContentReference] | None = None,
    ) -> None:
        """Broadcast the notification to all registered reporters."""
        for reporter in self._reporters:
            await reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=name,
                message=message,
                state=state,
                references=references,
            )
