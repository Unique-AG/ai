from __future__ import annotations

import re
from logging import getLogger

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.agentic.tools.experimental.recursive_summarize.config import (
    RecursiveSummarizeConfig,
)
from unique_toolkit.agentic.tools.experimental.recursive_summarize.message_log import (
    RecursiveSummarizeMessageLogger,
    RecursiveSummarizeMessageLoggerNoop,
    build_cited_reference_chunks,
    build_reference_chunks,
)
from unique_toolkit.agentic.tools.experimental.recursive_summarize.schemas import (
    RecursiveSummarizeInput,
)
from unique_toolkit.agentic.tools.experimental.recursive_summarize.service import (
    RecursiveSummarizerService,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import Content, ContentChunk
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import LanguageModelFunction

logger = getLogger(__name__)

_STILL_PROCESSING_MESSAGE = (
    "The uploaded document is still processing. "
    "Please wait for ingestion to finish and try again."
)

# Internal provenance marker threaded through the map-reduce pipeline. Each
# original chunk gets a stable global index (<<S12>>) that MAP tags onto facts
# and REDUCE preserves verbatim, so surviving markers in the final summary map
# every claim back to the exact source chunk it came from.
_SOURCE_MARKER_RE = re.compile(r"<<S(\d+)>>")


def _mark_chunk_text(index: int, text: str) -> str:
    return f"<<S{index}>> {text}"


def _clean_summary_spacing(text: str) -> str:
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)
    return text.strip()


class RecursiveSummarizeTool(Tool[RecursiveSummarizeConfig]):
    name: str = "RecursiveSummarize"

    def __init__(
        self,
        config: RecursiveSummarizeConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ) -> None:
        super().__init__(config, event, tool_progress_reporter)

    def display_name(self) -> str:
        return self.config.display_name

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=RecursiveSummarizeInput.model_json_schema(),
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.config.system_prompt

    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        try:
            input_data = RecursiveSummarizeInput.model_validate(tool_call.arguments)
        except Exception as exc:
            logger.warning("RecursiveSummarizeTool: input validation failed: %s", exc)
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                content=(
                    f"Error: invalid input — {exc}. "
                    "Provide a task_description describing what to summarize."
                ),
            )

        if self.config.language_model is None:
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                error_message="RecursiveSummarize is not configured with a language model.",
            )

        content_service = ContentService.from_event(self.event)
        try:
            if input_data.content_id:
                contents = await content_service.search_contents_async(
                    where={"id": {"in": [input_data.content_id]}},
                )
            else:
                contents = await content_service.search_contents_async(
                    where={"ownerId": {"equals": self.event.payload.chat_id}},
                )
        except Exception:
            logger.exception("RecursiveSummarizeTool: failed to fetch documents")
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                error_message="Failed to retrieve documents to summarize.",
            )

        new_answers_ui = feature_flags.enable_new_answers_ui_un_14411.is_enabled(
            self.event.company_id
        )
        message_logger = self._get_message_logger(new_answers_ui)

        if not contents:
            if input_data.content_id:
                return ToolCallResponse(
                    id=tool_call.id,
                    name=self.name,
                    content=(
                        f"Could not load content '{input_data.content_id}'. "
                        "Check that it has finished ingesting and that you have access "
                        "to it, then try again."
                    ),
                )
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                content=_STILL_PROCESSING_MESSAGE,
            )

        if not input_data.content_id and input_data.file_name:
            selected = [
                content
                for content in contents
                if self._matches_file_name(content, input_data.file_name)
            ]
            if not selected:
                available = ", ".join(
                    self._content_display_name(content) for content in contents
                )
                return ToolCallResponse(
                    id=tool_call.id,
                    name=self.name,
                    content=(
                        f"No uploaded file matches '{input_data.file_name}'. "
                        f"Available files: {available}. "
                        "Call the tool again with one of these exact names."
                    ),
                )
            contents = selected

        await message_logger.log_task(input_data.task_description)
        await message_logger.log_contents(contents)
        await message_logger.log_progress("_Summarizing document_")

        summarizer = RecursiveSummarizerService(
            language_model_service=self.language_model_service,
            config=self.config,
        )

        summarized_contents: list[Content] = []
        sections: list[tuple[str, str]] = []
        source_chunks: list[ContentChunk] = []
        try:
            for content in contents:
                ordered_chunks = [
                    chunk
                    for chunk in sorted(content.chunks, key=lambda item: item.order)
                    if chunk.text
                ]
                if not ordered_chunks:
                    continue
                marked_texts: list[str] = []
                for chunk in ordered_chunks:
                    # node-chat builds the reference name from ``title ?? key`` and the
                    # frontend parses the page from that name's postfix. Chunks from
                    # full-content search may not carry key/title, so inherit them from
                    # the parent document to keep citations named and page-linkable.
                    if not chunk.title:
                        chunk.title = content.title
                    if not chunk.key:
                        chunk.key = content.key
                    marked_texts.append(
                        _mark_chunk_text(len(source_chunks), chunk.text)
                    )
                    source_chunks.append(chunk)
                file_summary = await summarizer.summarize(
                    chunks=marked_texts,
                    task_description=input_data.task_description,
                )
                summarized_contents.append(content)
                sections.append((self._content_display_name(content), file_summary))
        except Exception as exc:
            logger.exception("RecursiveSummarizeTool: summarization failed")
            await message_logger.failed()
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                error_message=f"Summarization failed: {exc}",
            )

        if not sections:
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                content=_STILL_PROCESSING_MESSAGE,
            )

        if len(sections) == 1:
            combined = sections[0][1]
        else:
            combined = "\n\n".join(f"## {name}\n\n{text}" for name, text in sections)

        summary, reference_chunks = self._resolve_sources(combined, source_chunks)
        cited_reference_count = len(reference_chunks)
        used_marker_fallback = False
        if not reference_chunks:
            used_marker_fallback = True
            reference_chunks = build_reference_chunks(summarized_contents)

        chunks_missing_pages = sum(
            1
            for chunk in reference_chunks
            if chunk.start_page is None or chunk.start_page < 0
        )
        logger.info(
            "RecursiveSummarize citations: cited=%d fallback=%s total_chunks=%d "
            "missing_pages=%d pages=%s",
            cited_reference_count,
            used_marker_fallback,
            len(source_chunks),
            chunks_missing_pages,
            [
                (chunk.chunk_id, chunk.start_page, chunk.end_page)
                for chunk in reference_chunks[:20]
            ],
        )

        await message_logger.finished()

        if self.tool_progress_reporter and not new_answers_ui:
            document_names = "; ".join(
                self._content_display_name(content) for content in summarized_contents
            )
            progress_message = input_data.task_description
            if document_names:
                progress_message = f"{progress_message}; {document_names}"
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=f"**{self.display_name()}**",
                message=progress_message,
                state=ProgressState.FINISHED,
            )

        reminder_config = (
            self.config.experimental_features.tool_response_system_reminder
        )

        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content=summary,
            content_chunks=reference_chunks,
            include_source_chunks_in_tool_message=True,
            system_reminder=reminder_config.get_reminder_prompt_for_summary(
                summary,
                summary_in_tool_content=True,
            ),
            debug_info={
                "input": input_data.model_dump(),
                "file_count": len(sections),
                "chunk_count": len(source_chunks),
                "cited_reference_count": cited_reference_count,
                "reference_chunk_count": len(reference_chunks),
                "used_marker_fallback": used_marker_fallback,
                "chunks_missing_pages": chunks_missing_pages,
                "summary": summary,
            },
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []

    def _get_message_logger(
        self,
        new_answers_ui: bool,
    ) -> RecursiveSummarizeMessageLogger | RecursiveSummarizeMessageLoggerNoop:
        if new_answers_ui:
            return RecursiveSummarizeMessageLogger(
                message_step_logger=self._message_step_logger,
                tool_display_name=self.display_name(),
            )
        return RecursiveSummarizeMessageLoggerNoop()

    @staticmethod
    def _resolve_sources(
        summary: str,
        source_chunks: list[ContentChunk],
    ) -> tuple[str, list[ContentChunk]]:
        """Prune, renumber, and rewrite provenance markers into final citations.

        Collects the ``<<S{i}>>`` markers that survived the map-reduce passes (in
        order of first appearance), keeps only those source chunks, renumbers them
        compactly to ``0..k-1`` matching the emitted ``[sourceN]`` tags, and drops
        any dangling/invalid markers. Returns the rewritten summary and the ordered
        reference chunks (order is significant — it defines source numbering).
        """
        used_order: list[int] = []
        seen: set[int] = set()
        for match in _SOURCE_MARKER_RE.finditer(summary):
            index = int(match.group(1))
            if 0 <= index < len(source_chunks) and index not in seen:
                seen.add(index)
                used_order.append(index)

        remap = {
            global_index: position for position, global_index in enumerate(used_order)
        }

        def _replace(match: re.Match[str]) -> str:
            position = remap.get(int(match.group(1)))
            if position is None:
                return ""
            return f"[source{position}]"

        rewritten = _clean_summary_spacing(_SOURCE_MARKER_RE.sub(_replace, summary))
        reference_chunks = build_cited_reference_chunks(
            [source_chunks[index] for index in used_order]
        )
        return rewritten, reference_chunks

    @staticmethod
    def _content_display_name(content: Content) -> str:
        return content.title or content.key or content.id

    @staticmethod
    def _matches_file_name(content: Content, file_name: str) -> bool:
        target = file_name.strip().lower()
        if not target:
            return False
        candidates = [
            value.strip().lower()
            for value in (content.title, content.key, content.id)
            if value
        ]
        return any(
            target == candidate or target in candidate or candidate in target
            for candidate in candidates
        )
