"""Tests for RecursiveSummarize tool response shaping (context-safe history)."""

import json
from logging import getLogger

import pytest

from tests.test_obj_factory import get_event_obj
from unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
    HistoryManagerConfig,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.tools.experimental.recursive_summarize.message_log import (
    build_reference_chunks,
)
from unique_toolkit.agentic.tools.experimental.recursive_summarize.tool import (
    RecursiveSummarizeTool,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.content.schemas import Content, ContentChunk, ContentMetadata
from unique_toolkit.language_model.infos import LanguageModelInfo


@pytest.fixture
def large_content() -> Content:
    return Content(
        id="cont_abcdefghijklmnopqrstuv",
        key="report.pdf",
        title="Annual Report",
        chunks=[
            ContentChunk(
                id="cont_abcdefghijklmnopqrstuv",
                chunk_id=f"chunk_{index}",
                key="report.pdf",
                text=f"Long paragraph {index} " * 200,
                order=index,
                metadata=ContentMetadata(key="report.pdf", mime_type="application/pdf"),
            )
            for index in range(50)
        ],
    )


class TestRecursiveSummarizeToolResponse:
    @pytest.mark.ai
    def test_history_message__includes_summary_without_full_document_text(
        self,
        large_content: Content,
    ) -> None:
        summary = "Executive summary of the annual report."
        reference_chunks = build_reference_chunks([large_content])

        response = ToolCallResponse(
            id="call_1",
            name="RecursiveSummarize",
            content=summary,
            content_chunks=reference_chunks,
            include_source_chunks_in_tool_message=True,
            system_reminder="Cite with [sourceX].",
        )

        history_manager = HistoryManager(
            logger=getLogger("test"),
            event=get_event_obj("user_1", "company_1", "chat_1", "assistant_1"),
            config=HistoryManagerConfig(),
            language_model=LanguageModelInfo.from_name("AZURE_GPT_4o_2024_1120"),
            reference_manager=ReferenceManager(),
        )
        tool_message = history_manager._get_tool_call_result_for_loop_history(response)

        assert summary in tool_message.content
        assert "Long paragraph" not in tool_message.content

        parts = tool_message.content.split("\n\n")
        assert parts[0] == summary
        sources = json.loads(parts[1])
        assert len(sources) == 1
        assert sources[0]["content"] == ""
        assert "Cite with [sourceX]." in parts[2]


def _chunk(index: int, text: str) -> ContentChunk:
    return ContentChunk(
        id="cont_abcdefghijklmnopqrstuv",
        chunk_id=f"chunk_{index}",
        key="report.pdf",
        text=text,
        order=index,
    )


class TestResolveSources:
    @pytest.mark.ai
    def test_resolve_sources__renumbers_by_first_appearance(self) -> None:
        source_chunks = [_chunk(i, f"passage {i}") for i in range(5)]
        summary = (
            "Assets reached 9.49 billion <<S3>>. Revenue rose <<S1>>. "
            "Assets are audited <<S3>>."
        )

        rewritten, references = RecursiveSummarizeTool._resolve_sources(
            summary, source_chunks
        )

        assert "<<S" not in rewritten
        assert "Assets reached 9.49 billion [source0]." in rewritten
        assert "Revenue rose [source1]." in rewritten
        assert "Assets are audited [source0]." in rewritten
        assert [chunk.chunk_id for chunk in references] == ["chunk_3", "chunk_1"]
        assert references[0].text == "passage 3"

    @pytest.mark.ai
    def test_resolve_sources__drops_invalid_markers(self) -> None:
        source_chunks = [_chunk(0, "only passage")]
        summary = "A fact <<S0>>. An out-of-range fact <<S9>>."

        rewritten, references = RecursiveSummarizeTool._resolve_sources(
            summary, source_chunks
        )

        assert rewritten == "A fact [source0]. An out-of-range fact."
        assert len(references) == 1

    @pytest.mark.ai
    def test_resolve_sources__no_markers_returns_empty_references(self) -> None:
        source_chunks = [_chunk(0, "passage")]
        summary = "A plain summary with no markers."

        rewritten, references = RecursiveSummarizeTool._resolve_sources(
            summary, source_chunks
        )

        assert rewritten == "A plain summary with no markers."
        assert references == []
