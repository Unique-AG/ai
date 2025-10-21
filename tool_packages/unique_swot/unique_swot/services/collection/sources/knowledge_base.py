from logging import getLogger

from unique_toolkit import KnowledgeBaseService
from unique_toolkit.content import ContentChunk
from unique_toolkit.content.schemas import (
    ContentInfo,
)

from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.collection.schema import Source, SourceChunk, SourceType

_LOGGER = getLogger(__name__)


def collect_knowledge_base(
    *,
    knowledge_base_service: KnowledgeBaseService,
    metadata_filter: dict,
    chunk_registry: ContentChunkRegistry,
) -> list[Source]:
    contents = knowledge_base_service.get_paginated_content_infos(
        metadata_filter=metadata_filter
    )
    sources = _convert_content_to_sources(
        knowledge_base_service=knowledge_base_service,
        content_infos=contents.content_infos,
        chunk_registry=chunk_registry,
    )

    return sources


def _convert_content_to_sources(
    *,
    knowledge_base_service: KnowledgeBaseService,
    content_infos: list[ContentInfo],
    chunk_registry: ContentChunkRegistry,
) -> list[Source]:
    sources = []
    sources_with_no_chunks = []
    for content_info in content_infos:
        title = content_info.title or content_info.key or "Unknown Title"
        url = content_info.url
        chunks = _get_chunks_from_content(
            knowledge_base_service=knowledge_base_service,
            content_id=content_info.id,
            chunk_registry=chunk_registry,
        )
        if len(chunks) == 0:
            sources_with_no_chunks.append(title)
            continue

        sources.append(
            Source(
                type=SourceType.INTERNAL_DOCUMENT,
                url=url,
                title=title,
                chunks=chunks,
            )
        )

    if len(sources_with_no_chunks) > 0:
        no_chunks_str = "\n- ".join(sources_with_no_chunks)
        _LOGGER.warning(
            f"The following internal documents have no chunks: \n- {no_chunks_str}"
        )

    return sources


def _get_chunks_from_content(
    *,
    knowledge_base_service: KnowledgeBaseService,
    content_id: str,
    chunk_registry: ContentChunkRegistry,
) -> list[SourceChunk]:
    contents = knowledge_base_service.search_contents(
        where={"id": {"equals": content_id}}
    )

    assert len(contents) == 1, (
        "Expected exactly one content to be found for the given content id"
    )

    chunks = []
    for chunk in sorted(contents[0].chunks, key=lambda x: x.order):
        text = chunk.text
        chunk_id = chunk_registry.add(chunk)
        chunks.append(SourceChunk(id=chunk_id, text=text))

    return chunks


def _clean_up_content_chunk(content_chunk: ContentChunk) -> ContentChunk:
    content_chunk.text = ""
    return content_chunk
