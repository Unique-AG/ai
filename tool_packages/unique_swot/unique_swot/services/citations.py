import re
from logging import getLogger

from unique_toolkit.content.schemas import ContentChunk, ContentReference

from unique_swot.services.collection.registry import ContentChunkRegistry

_LOGGER = getLogger(__name__)


class CitationManager:
    def __init__(self, content_chunk_registry: ContentChunkRegistry):
        self._content_chunk_registry = content_chunk_registry
        self._citations_map = {}
        self._content_chunks: list[ContentChunk] = []

    def process_result(self, report: str) -> str:
        # Find all citation tags in the format [chunk_<id>] in the report, where <id> can be a uuid (alphanumeric and hyphens)
        citations = re.findall(r"\[chunk_([a-zA-Z0-9\-]+)\]", report)
        for citation in citations:
            # Check if this citation has already been assigned a superscript (to maintain consistent numbering)
            if citation in self._citations_map:
                replace_with = self._citations_map[citation]
            else:
                # Assign the next superscript number to this new citation
                chunk = self._content_chunk_registry.retrieve(f"chunk_{citation}")
                if chunk is not None:
                    length = len(self._citations_map)
                    replace_with = f"<sup>{length + 1}</sup>"
                    self._citations_map[citation] = replace_with
                    self._content_chunks.append(chunk)
                else:
                    _LOGGER.warning(f"Chunk {citation} not found in registry")
                    replace_with = f"[chunk_{citation}]"
            # Replace the citation tag in the report with the superscript (formatted as HTML)
            report = report.replace(f"[chunk_{citation}]", replace_with)
        # Return the processed report text with all citation tags replaced by their superscripts
        return report

    def get_references(self, message_id: str) -> list[ContentReference]:
        return [
            _convert_content_chunk_to_content_reference(message_id, index, chunk)
            for index, chunk in enumerate(self._content_chunks)
        ]

    def get_referenced_content_chunks(self) -> list[ContentChunk]:
        return self._content_chunks


def _convert_content_chunk_to_content_reference(
    message_id: str, index: int, chunk: ContentChunk
) -> ContentReference:
    url = f"unique//content/{chunk.id}"
    source_id = f"{chunk.id}_{chunk.chunk_id}"
    filename = chunk.title or chunk.key or "Unknown Title"
    pages = _get_pages(chunk.start_page, chunk.end_page)
    title = f"{filename}{pages}"
    return ContentReference(
        url=url,
        source_id=source_id,
        message_id=message_id,
        name=title,
        sequence_number=index,
        source="SWOT-TOOL",
    )


def _get_pages(start_page: int | None, end_page: int | None) -> str:
    if start_page is None:
        return ""
    if end_page is None:
        return f": {start_page}"
    return f": {start_page}, {end_page}"
