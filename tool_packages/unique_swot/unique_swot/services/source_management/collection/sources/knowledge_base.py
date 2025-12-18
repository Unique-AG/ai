from logging import getLogger

from unique_toolkit import KnowledgeBaseService
from unique_toolkit.content import Content
from unique_toolkit.content.schemas import (
    ContentInfo,
)

_LOGGER = getLogger(__name__)


async def collect_knowledge_base(
    *,
    knowledge_base_service: KnowledgeBaseService,
    metadata_filter: dict,
) -> list[Content]:
    contents = knowledge_base_service.get_paginated_content_infos(
        metadata_filter=metadata_filter
    )
    contents = await _get_contents_from_paginated_content_infos(
        knowledge_base_service=knowledge_base_service,
        content_infos=contents.content_infos,
    )

    return contents


async def _get_contents_from_paginated_content_infos(
    *,
    knowledge_base_service: KnowledgeBaseService,
    content_infos: list[ContentInfo],
) -> list[Content]:
    contents: list[Content] = []
    for content_info in content_infos:
        content = await _get_chunks_from_content(
            knowledge_base_service=knowledge_base_service,
            content_id=content_info.id,
        )

        if content is None:
            _LOGGER.warning(
                f"No content found for the given content id. Check Ingestion Status: {content_info.id} for more details."
            )
            continue

        if len(content.chunks) == 0:
            _LOGGER.warning(
                f"No chunks found for the given content id. Check Ingestion Status: {content_info.id} for more details."
            )
            continue

        contents.append(content)

    return contents


async def _get_chunks_from_content(
    *,
    knowledge_base_service: KnowledgeBaseService,
    content_id: str,
) -> Content | None:
    contents = await knowledge_base_service.search_contents_async(
        where={"id": {"equals": content_id}}
    )

    if len(contents) == 0:
        _LOGGER.warning(
            f"No content found for the given content id. Check Ingestion Status: {content_id}"
        )
        return

    if len(contents) > 1:
        _LOGGER.warning(
            "Expected exactly one content to be found for the given content id."
            f" Found {len(contents)} contents for the given content id: {content_id}"
            f" Returning the first content."
        )

    return contents[0]
