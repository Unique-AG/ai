from unique_toolkit import KnowledgeBaseService
from unique_toolkit.content.schemas import Content

from unique_swot.services.schemas import Source, SourceType


def collect_knowledge_base(
    *, knowledge_base_service: KnowledgeBaseService, where_clause: dict
) -> list[Source]:
    contents = knowledge_base_service.search_contents(where=where_clause)
    sources = []

    for content in contents:
        sources.extend(_convert_content_to_sources(content))

    return sources


def _convert_content_to_sources(content: Content) -> list[Source]:
    return [
        Source(
            type=SourceType.INTERNAL_DOCUMENT,
            source_id=chunk.id,
            content=chunk.text,
        )
        for chunk in content.chunks
    ]
