from unique_toolkit.content import Content

from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.collection.schema import SourceChunk


def convert_content_to_sources(
    content: Content, chunk_registry: ContentChunkRegistry
) -> list[SourceChunk]:
    chunks = []
    for chunk in sorted(content.chunks, key=lambda x: x.order):
        text = chunk.text
        chunk_id = chunk_registry.register_and_generate_id(chunk)
        chunks.append(SourceChunk(id=chunk_id, text=text))

    return chunks
