from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.chat.schemas import (
    MessageLog,
    MessageLogDetails,
    MessageLogEvent,
    MessageLogStatus,
)
from unique_toolkit.content.schemas import Content, ContentChunk, ContentReference
from unique_toolkit.content.utils import _generate_pages_postfix, sort_content_chunks


class RecursiveSummarizeMessageLoggerNoop:
    async def log_task(self, task_description: str) -> None:
        pass

    async def log_contents(self, contents: list[Content]) -> None:
        pass

    async def log_progress(self, progress_message: str) -> None:
        pass

    async def finished(self) -> None:
        pass

    async def failed(self) -> None:
        pass


def representative_chunk(content: Content) -> ContentChunk | None:
    if content.chunks:
        return min(content.chunks, key=lambda chunk: chunk.order)
    if not content.id:
        return None
    return ContentChunk(
        id=content.id,
        key=content.key or content.title,
        title=content.title,
        text="",
        order=0,
    )


def build_reference_chunks(contents: list[Content]) -> list[ContentChunk]:
    """One lightweight chunk per content for citation plumbing without full document text.

    Fallback used only when the summary carries no surviving source markers.
    """
    chunks: list[ContentChunk] = []
    for content in contents:
        chunk = representative_chunk(content)
        if chunk is None:
            continue
        stub = chunk.model_copy(deep=True)
        stub.text = ""
        chunks.append(stub)
    if not chunks:
        return []
    return sort_content_chunks(chunks)


def build_cited_reference_chunks(chunks: list[ContentChunk]) -> list[ContentChunk]:
    """Reference chunks for the chunks actually cited in the summary.

    Order is significant: the history manager assigns ``source_number`` by list
    position, so ``result[N]`` becomes ``[sourceN]`` (modulo a conversation-level
    offset). The list must NOT be re-sorted. Real chunk text/identity is kept so
    the backend can resolve the correct highlight in the source document.

    The page postfix (e.g. ``" : 9"``) is appended to ``key``/``title`` per chunk —
    node-chat builds the reference name from ``title ?? key`` verbatim (it does not
    read ``startPage``), and the frontend parses the page to deep-link. This mirrors
    what the search modules do via ``sort_content_chunks``, but without the reorder
    that would misalign source numbers.
    """
    reference_chunks: list[ContentChunk] = []
    for chunk in chunks:
        copy = chunk.model_copy(deep=True)
        pages_postfix = _generate_pages_postfix([copy])
        if pages_postfix:
            if copy.key:
                copy.key = f"{copy.key}{pages_postfix}"
            if copy.title:
                copy.title = f"{copy.title}{pages_postfix}"
        reference_chunks.append(copy)
    return reference_chunks


def content_to_reference(content: Content, sequence_number: int) -> ContentReference:
    chunk = representative_chunk(content)
    if chunk is not None:
        return chunk.to_reference(sequence_number)

    name = content.title or content.key or f"Content {content.id}"
    return ContentReference(
        name=name,
        sequence_number=sequence_number,
        source="node-ingestion-chunks",
        source_id=content.id,
        url=f"unique://content/{content.id}",
    )


class RecursiveSummarizeMessageLogger:
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
        self._message = "_Summarization failed_"
        self._status = MessageLogStatus.FAILED
        await self._propagate_message_log()

    async def log_progress(self, progress_message: str) -> None:
        self._message = progress_message
        await self._propagate_message_log()

    async def log_task(self, task_description: str) -> None:
        self._details.data.extend(  # type: ignore[union-attr]
            [
                MessageLogEvent(
                    type="InternalSearch",
                    text=task_description,
                )
            ]
        )
        await self._propagate_message_log()

    async def log_contents(self, contents: list[Content]) -> None:
        offset_sequence_number = len(self._references)
        new_references = [
            content_to_reference(content, sequence_number)
            for sequence_number, content in enumerate(
                contents, start=offset_sequence_number
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
