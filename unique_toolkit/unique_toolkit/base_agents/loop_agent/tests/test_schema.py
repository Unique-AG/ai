import pytest
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.tools.agent_chunks_handler import AgentChunksHandler


def create_content_chunk(
    id: str, chunk_id: str, text: str = "test", order: int = 1
) -> ContentChunk:
    return ContentChunk(id=id, chunk_id=chunk_id, text=text, order=order)


class TestAgentChunksHandler:
    @pytest.fixture
    def handler(self):
        return AgentChunksHandler()

    def test_initial_state(self, handler):
        assert handler.chunks == []
        assert handler.tool_chunks == {}
        assert handler.all_references == []
        assert handler.latest_references == []
        assert handler.latest_referenced_chunks == []

    def test_extend_chunks(self, handler):
        chunks = [
            create_content_chunk("1", "1"),
            create_content_chunk("2", "1"),
        ]
        handler.extend(chunks)
        assert handler.chunks == chunks

        # Test extending existing chunks
        more_chunks = [create_content_chunk("3", "1")]
        handler.extend(more_chunks)
        assert len(handler.chunks) == 3

    def test_replace_chunks(self, handler):
        initial_chunks = [create_content_chunk("1", "1")]
        handler.extend(initial_chunks)

        new_chunks = [
            create_content_chunk("2", "1"),
            create_content_chunk("3", "1"),
        ]
        handler.replace(new_chunks)
        assert handler.chunks == new_chunks

    def test_references_handling(self, handler):
        chunks = [
            create_content_chunk("1", "1", text="test1", order=1),
            create_content_chunk("2", "1", text="test2", order=2),
            create_content_chunk("3", "1", text="test3", order=3),
        ]
        handler.extend(chunks)

        references = [
            {
                "id": "1",
                "messageId": "1",
                "name": "test",
                "sequenceNumber": 1,
                "source": "test",
                "sourceId": "1_1",
                "url": "test",
            },
            {
                "id": "2",
                "messageId": "2",
                "name": "test",
                "sequenceNumber": 2,
                "source": "test",
                "sourceId": "2_1",
                "url": "test",
            },
        ]
        references = [ContentReference(**reference) for reference in references]

        handler.add_references(references)

        assert len(handler.all_references) == 1

        # Test referenced chunks
        referenced_chunks: list[ContentChunk] = handler.latest_referenced_chunks
        assert len(referenced_chunks) == 2
        assert referenced_chunks[0].id == "1"
        assert referenced_chunks[1].id == "2"

        # Add another set of references
        new_references = [
            ContentReference(
                **{
                    "id": "3",
                    "messageId": "3",
                    "name": "test",
                    "sequenceNumber": 3,
                    "source": "test",
                    "sourceId": "3_1",
                    "url": "test",
                }
            ),
        ]
        handler.add_references(new_references)

        assert len(handler.all_references) == 2
        assert len(handler.latest_referenced_chunks) == 1
        assert handler.latest_referenced_chunks[0].id == "3"  # type: ignore
