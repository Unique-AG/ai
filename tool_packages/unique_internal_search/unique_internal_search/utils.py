import logging
import re

from pydantic import BaseModel
from unique_toolkit.content.schemas import ContentChunk

_LOGGER = logging.getLogger(__name__)


class SearchStringResult(BaseModel):
    query: str
    chunks: list[ContentChunk]


def interleave_search_results_round_robin(
    search_results: list[SearchStringResult],
) -> list[SearchStringResult]:
    """
    Interleave search results from multiple search queries using round-robin strategy. Search results with duplicate chunks are removed (keeping first occurrence).

    Example:
        Query 1: [SearchStringResult(query="query1", chunks=[ContentChunk(chunk_id="A"), ContentChunk(chunk_id="B"), ContentChunk(chunk_id="C")])]
        Query 2: [SearchStringResult(query="query2", chunks=[ContentChunk(chunk_id="D"), ContentChunk(chunk_id="E")])]
        Query 3: [SearchStringResult(query="query3", chunks=[ContentChunk(chunk_id="F"), ContentChunk(chunk_id="G"), ContentChunk(chunk_id="H"), ContentChunk(chunk_id="I")])]
        Result: [SearchStringResult(query="query1", chunks=[ContentChunk(chunk_id="A"), ContentChunk(chunk_id="D"), ContentChunk(chunk_id="F")]), SearchStringResult(query="query2", chunks=[ContentChunk(chunk_id="B"), ContentChunk(chunk_id="E")]), SearchStringResult(query="query3", chunks=[ContentChunk(chunk_id="C"), ContentChunk(chunk_id="G"), ContentChunk(chunk_id="H"), ContentChunk(chunk_id="I")])]
    """
    if not search_results:
        return []

    max_chunks = max(len(result.chunks) for result in search_results)
    interleaved_search_results: list[SearchStringResult] = [
        result
        for i in range(max_chunks)
        for result in search_results
        if i < len(result.chunks)
    ]

    return _deduplicate_search_results(interleaved_search_results)


def _deduplicate_search_results(
    search_results: list[SearchStringResult],
) -> list[SearchStringResult]:
    """Remove duplicate chunks by chunk_id, preserving order (keeping first occurrence)."""
    seen_chunk_ids: set[str] = set()
    deduplicated_search_results: list[SearchStringResult] = []

    for result in search_results:
        for chunk in result.chunks:
            if chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk.chunk_id)
                deduplicated_search_results.append(result)

        if removed := len(result.chunks) - len(deduplicated_search_results):
            _LOGGER.info(
                f"Removed {removed} duplicate chunks ({len(deduplicated_search_results)}/{len(result.chunks)} unique)"
            )

    return deduplicated_search_results


def append_metadata_in_chunks(
    chunks: list[ContentChunk],
    metadata_chunk_sections: dict[str, str] | None = None,
) -> list[ContentChunk]:
    """
    Append metadata to chunks.
    Args:
        chunks: List of ContentChunk objects
        metadata_chunk_sections: Dictionary of metadata sections to add to the chunk text
    Returns:
        List of ContentChunk objects with metadata appended
    """
    if metadata_chunk_sections is None:
        return chunks
    for chunk in chunks:
        if chunk.metadata is None:
            continue
        chunk = _append_metadata_in_chunk(
            chunk=chunk, metadata_chunk_sections=metadata_chunk_sections
        )
    return chunks


def _append_metadata_in_chunk(
    chunk: ContentChunk, metadata_chunk_sections: dict[str, str]
) -> ContentChunk:
    """
    Format chunk text by prepending metadata according to sections config.
    Args:
        chunk: ContentChunk object
        metadata_chunk_sections: Dictionary of metadata sections to add to the chunk text
    Returns:
        Formatted text with metadata prepended
    """
    meta_dict = chunk.metadata.model_dump(exclude_none=True, by_alias=True)

    parts: list[str] = []
    for key, template in metadata_chunk_sections.items():
        if key in meta_dict:
            formatted_section = template.format(meta_dict[key])
            parts.append(formatted_section)

    # Combine metadata parts with the main text
    if parts:
        chunk.text = "\n".join(parts) + "\n" + chunk.text

    return chunk


def clean_search_string(search_string: str) -> str:
    """
    Remove QDF (QueryDeservedFreshness) and boost operators from search string.

    Examples:
        '+(GPT4) performance on +(MMLU) benchmark --QDF=1'
        -> 'GPT4 performance on MMLU benchmark'

        'Best practices for +(security) and +(privacy) for +(cloud storage) --QDF=2'
        -> 'Best practices for security and privacy for cloud storage'

    Args:
        search_string: Raw search string that may contain operators

    Returns:
        Cleaned search string without operators
    """
    # Remove --QDF=<number> operator (at the end of the string)
    cleaned = re.sub(r"\s*--QDF=\d+\s*$", "", search_string)

    # Remove +(...) boost operators - replace with just the content inside parentheses
    cleaned = re.sub(r"\+\(([^)]+)\)", r"\1", cleaned)

    # Clean up any extra whitespace
    cleaned = " ".join(cleaned.split())

    return cleaned.strip()
