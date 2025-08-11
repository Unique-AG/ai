import pytest
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelToolMessage,
)
from unique_toolkit.unique_toolkit.base_agents.loop_agent.schemas import AgentChunksHandler
from unique_toolkit.unique_toolkit.base_agents.loop_agent.utils.history_manipulation import _create_reduced_empty_sources_message, _create_reduced_standard_sources_message, _create_reduced_table_search_message, reduce_message_length_by_reducing_sources_in_tool_response, remove_suggested_questions_from_history



class TestSuggestedQuestionsRemoval:
    @pytest.fixture
    def message_with_suggestions(self) -> LanguageModelAssistantMessage:
        return LanguageModelAssistantMessage(
            content=(
                "Here's the main content.\n\n"
                "---\n\n"
                "_Suggested follow-up questions:_\n\n"
                "1. Question 1?\n"
                "2. Question 2?"
            )
        )

    def test_removes_suggested_questions(self, message_with_suggestions):
        """Should remove suggested questions section while preserving main content"""
        history = [message_with_suggestions]

        result = remove_suggested_questions_from_history(history)

        assert len(result) == 1
        assert result[0].content == "Here's the main content."
        assert "_Suggested follow-up questions:_" not in result[0].content


class TestSourceReduction:
    @pytest.fixture
    def chunks(self) -> list[ContentChunk]:
        return [
            ContentChunk(text="Source 1", id="1", order=0),
            ContentChunk(text="Source 2", id="2", order=1),
        ]

    @pytest.fixture
    def chunks_handler(self, chunks) -> AgentChunksHandler:
        handler = AgentChunksHandler()
        handler.replace(chunks)
        handler._tool_chunks = {"test_call_1": {"chunks": chunks}}
        return handler

    @pytest.fixture
    def tool_message(self) -> LanguageModelToolMessage:
        return LanguageModelToolMessage(
            content=[
                {"source_number": 0, "content": "Source 1"},
                {"source_number": 1, "content": "Source 2"},
            ],
            tool_call_id="test_call_1",
            name="test_tool",
        )

    def test_reduces_single_tool_message(self, chunks_handler, tool_message):
        """Should reduce sources in a single tool message by removing the last source"""
        history = [tool_message]

        (
            result,
            updated_handler,
        ) = reduce_message_length_by_reducing_sources_in_tool_response(
            history, chunks_handler
        )

        assert len(result) == 1
        assert len(updated_handler.tool_chunks["test_call_1"]["chunks"]) == 1
        assert "Source 1" in str(result[0].content)
        assert "Source 2" not in str(result[0].content)

    def test_handles_empty_sources(self, chunks_handler):
        """Should handle tool messages with no sources gracefully"""
        empty_message = LanguageModelToolMessage(
            content="No relevant sources found.",
            tool_call_id="empty_call",
            name="test_tool",
        )
        chunks_handler.tool_chunks["empty_call"] = {"chunks": []}
        history: list[LanguageModelMessage] = [empty_message]

        (
            result,
            updated_handler,
        ) = reduce_message_length_by_reducing_sources_in_tool_response(
            history, chunks_handler
        )

        assert len(result) == 1
        assert result[0].content == "No relevant sources found."
        assert updated_handler.tool_chunks["empty_call"]["chunks"] == []

    def test_handles_mixed_message_types(self, chunks_handler, tool_message):
        """Should correctly process a mix of message types"""
        assistant_message = LanguageModelAssistantMessage(
            content="Some response"
        )
        tool_message_1 = LanguageModelToolMessage(
            content="[{'source_number': 0, 'content': 'Source 1'}, {'source_number': 1, 'content': 'Source 2'}]",
            tool_call_id="test_call_1",
            name="test_tool",
        )
        tool_message_2 = LanguageModelToolMessage(
            content="[{'source_number': 2, 'content': 'Source 3'}, {'source_number': 3, 'content': 'Source 4'}]",
            tool_call_id="test_call_2",
            name="test_tool",
        )
        history: list[LanguageModelMessage] = [
            tool_message_1,
            assistant_message,
            tool_message_2,
        ]

        handler: AgentChunksHandler = AgentChunksHandler()
        chunks: list[ContentChunk] = [
            ContentChunk(text="Source 1", id="1", order=0),
            ContentChunk(text="Source 2", id="2", order=1),
            ContentChunk(text="Source 3", id="3", order=2),
            ContentChunk(text="Source 4", id="4", order=3),
        ]
        handler.replace(chunks)
        handler._tool_chunks = {
            "test_call_1": {"chunks": chunks[:2]},
            "test_call_2": {"chunks": chunks[2:]},
        }

        (
            result,
            updated_handler,
        ) = reduce_message_length_by_reducing_sources_in_tool_response(
            history, handler
        )

        assert len(result) == 3
        assert isinstance(
            result[1], LanguageModelAssistantMessage
        )  # Assistant message unchanged
        assert isinstance(result[0].content, str)
        assert isinstance(result[2].content, str)
        assert "Source 1" in result[0].content
        assert "Source 2" not in result[0].content
        assert "Source 3" in result[2].content
        assert "Source 4" not in result[2].content


class TestCreateToolCallMessageWithReducedSources:
    @pytest.fixture
    def base_tool_message(self) -> LanguageModelToolMessage:
        return LanguageModelToolMessage(
            content="Original content",
            tool_call_id="test_call_1",
            name="test_tool",
        )

    @pytest.fixture
    def base_content_chunks(self) -> list[ContentChunk]:
        return [
            ContentChunk(text="Source 1 content", id="1", order=0),
            ContentChunk(text="Source 2 content", id="2", order=1),
        ]

    @pytest.fixture
    def table_search_content(self) -> list[ContentChunk]:
        return [
            ContentChunk(text="Table search result", id="1", order=0),
        ]

    def test_creates_table_search_message_with_content(
        self, base_tool_message, table_search_content
    ):
        """Should create TableSearch message with proper source formatting when chunks exist"""
        table_search_message = LanguageModelToolMessage(
            content='{"source_number": 0, "content": [{"Name": "Apple Inc."}]}',
            tool_call_id="table_call",
            name="TableSearch",
        )

        result = _create_reduced_table_search_message(
            table_search_message, table_search_content, source_offset=5
        )

        assert result.name == "TableSearch"
        assert result.tool_call_id == "table_call"
        assert isinstance(result.content, str)
        assert (
            result.content
            == '{"source_number": 5, "content": [{"Name": "Apple Inc."}]}'
        )

    def test_creates_table_search_message_without_content(
        self, base_tool_message
    ):
        """Should create TableSearch message with original content when no chunks"""
        table_search_message = LanguageModelToolMessage(
            content="Error message",
            tool_call_id="table_call",
            name="TableSearch",
        )

        result = _create_reduced_table_search_message(
            message=table_search_message, content_chunks=[], source_offset=0
        )

        assert result.name == "TableSearch"
        assert result.tool_call_id == "table_call"
        assert result.content == "Error message"

    def test_creates_empty_sources_message(self, base_tool_message):
        """Should create message with 'No relevant sources found' when no content chunks"""
        result = _create_reduced_empty_sources_message(base_tool_message)

        assert result.name == "test_tool"
        assert result.tool_call_id == "test_call_1"
        assert result.content == "No relevant sources found."

    def test_creates_standard_sources_message(
        self, base_tool_message, base_content_chunks
    ):
        """Should create standard message with properly formatted sources"""
        result = _create_reduced_standard_sources_message(
            base_tool_message, base_content_chunks, source_offset=10
        )

        assert result.name == "test_tool"
        assert result.tool_call_id == "test_call_1"
        assert isinstance(result.content, str)

        # Check that content contains the expected source information
        content_str = result.content
        assert "Source 1 content" in content_str
        assert "Source 2 content" in content_str
        assert "10" in content_str  # source_number for first chunk
        assert "11" in content_str  # source_number for second chunk

    def test_source_offset_calculation(
        self, base_tool_message, base_content_chunks
    ):
        """Should correctly apply source offset to source numbers"""
        result = _create_reduced_standard_sources_message(
            base_tool_message, base_content_chunks, source_offset=100
        )

        content_str = result.content
        assert isinstance(content_str, str)
        assert "100" in content_str  # First source number
        assert "101" in content_str  # Second source number

    def test_single_content_chunk_handling(self, base_tool_message):
        """Should handle single content chunk correctly"""
        single_chunk = [ContentChunk(text="Single source", id="1", order=0)]

        result = _create_reduced_standard_sources_message(
            base_tool_message, single_chunk, source_offset=0
        )

        assert isinstance(result.content, str)
        assert "Single source" in result.content
        assert "0" in result.content  # source_number
