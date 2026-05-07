from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.chat.schemas import (
    MessageLog,
    MessageLogDetails,
    MessageLogEvent,
    MessageLogStatus,
)
from unique_toolkit.content.schemas import ContentChunk, ContentReference


class InternalSearchMessageLoggerNoop:
    async def log_progress(self, progress_message: str) -> None:
        pass

    async def log_queries(self, queries: list[str]) -> None:
        pass

    async def log_chunks(self, chunks: list[ContentChunk]) -> None:
        pass

    async def finished(self) -> None:
        pass

    async def failed(self) -> None:
        pass


class InternalSearchMessageLogger:
    def __init__(self, message_step_logger: MessageStepLogger, tool_display_name: str):
        self._message_step_logger = message_step_logger
        self._current_message_log: MessageLog | None = None
        self._tool_display_name = tool_display_name

        self._status = MessageLogStatus.RUNNING
        self._details: MessageLogDetails = MessageLogDetails(data=[])
        self._references: list[ContentReference] = []
        self._message = ""

    async def finished(self) -> None:
        self._message = ""
        self._status = MessageLogStatus.COMPLETED
        await self._propagate_message_log()

    async def failed(self) -> None:
        self._message = "_Search failed_"
        self._status = MessageLogStatus.FAILED
        await self._propagate_message_log()

    async def log_progress(self, progress_message: str) -> None:
        self._message = progress_message
        await self._propagate_message_log()

    async def log_queries(self, queries: list[str]) -> None:
        log_events_from_queries = [
            MessageLogEvent(
                type="InternalSearch",
                text=query,
            )
            for query in queries
        ]
        self._details.data.extend(log_events_from_queries)  # type: ignore (data has already been initialized with an empty list)
        await self._propagate_message_log()

    async def log_chunks(self, chunks: list[ContentChunk]) -> None:
        offset_sequence_number = len(self._references)
        new_references = [
            ContentReference(
                name=chunk.title or chunk.key or "",
                sequence_number=sequence_number,
                source="internal",
                source_id=chunk.id,
                url=f"unique://content/{chunk.id}",
            )
            for sequence_number, chunk in enumerate(
                chunks, start=offset_sequence_number
            )
        ]
        self._references.extend(new_references)
        await self._propagate_message_log()

    async def _propagate_message_log(self) -> None:
        self._current_message_log = (
            await self._message_step_logger.create_or_update_message_log_async(
                active_message_log=self._current_message_log,
                header=self._tool_display_name,
                progress_message=self._message,
                details=self._details,
                references=self._references,
                status=self._status,
            )
        )
