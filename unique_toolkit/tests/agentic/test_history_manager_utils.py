import json

import pytest

from unique_toolkit.agentic.history_manager.utils import transform_chunks_to_string
from unique_toolkit.content.schemas import ContentChunk


def create_content_chunk(
    chunk_id: str,
    text: str,
    order: int = 0,
) -> ContentChunk:
    return ContentChunk(
        id=f"cont_{chunk_id}",
        chunk_id=chunk_id,
        text=text,
        order=order,
        key="test_file.pdf",
    )


@pytest.mark.ai
def test_transform_chunks_to_string__preserves_readable_unicode_and_round_trips_AI() -> (
    None
):
    """Unicode source text should remain readable in the serialized tool payload."""
    content_chunks = [
        create_content_chunk(
            "chunk_1",
            "ページ名 cafe déjà مرحبا שלום 😀",
        )
    ]

    serialized_sources, sources = transform_chunks_to_string(
        content_chunks,
        max_source_number=7,
    )

    assert sources == [
        {
            "source_number": 7,
            "content_id": "cont_chunk_1",
            "content": "ページ名 cafe déjà مرحبا שלום 😀",
        }
    ]
    assert "ページ名" in serialized_sources
    assert "déjà" in serialized_sources
    assert "مرحبا" in serialized_sources
    assert "שלום" in serialized_sources
    assert "😀" in serialized_sources
    assert "\\u30da" not in serialized_sources
    assert json.loads(serialized_sources) == sources


@pytest.mark.ai
def test_transform_chunks_to_string__preserves_json_sensitive_characters_AI() -> None:
    """The JSON string should remain valid while round-tripping quotes and newlines."""
    text = 'ページ名 "quoted" path\\\\segment\nnext line'
    content_chunks = [create_content_chunk("chunk_2", text)]

    serialized_sources, _ = transform_chunks_to_string(
        content_chunks,
        max_source_number=0,
    )

    assert "ページ名" in serialized_sources
    decoded_sources = json.loads(serialized_sources)
    assert decoded_sources[0]["content"] == text


@pytest.mark.ai
def test_transform_chunks_to_string__returns_empty_message_for_empty_chunks_AI() -> (
    None
):
    """Empty search results should keep the established no-results contract."""
    serialized_sources, sources = transform_chunks_to_string([], max_source_number=0)

    assert serialized_sources == "No relevant sources found."
    assert sources == []


@pytest.mark.ai
def test_transform_chunks_to_string__starts_source_numbers_from_offset_AI() -> None:
    """Source numbering should continue from the provided offset."""
    content_chunks = [
        create_content_chunk("chunk_3", "最初の結果", order=1),
        create_content_chunk("chunk_4", "二番目の結果", order=2),
    ]

    serialized_sources, _ = transform_chunks_to_string(
        content_chunks,
        max_source_number=3,
    )

    decoded_sources = json.loads(serialized_sources)
    assert decoded_sources[0]["source_number"] == 3
    assert decoded_sources[1]["source_number"] == 4
    assert decoded_sources[0]["content"] == "最初の結果"
    assert decoded_sources[1]["content"] == "二番目の結果"
