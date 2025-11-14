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
    Interleave chunks from multiple search queries using a round-robin strategy.
    Each result in the output contains a single chunk. Duplicate chunks are removed,
    keeping the first occurrence.

    Example:
        Input:
            Query 1: SearchStringResult(query="query1", chunks=[A, B, C])
            Query 2: SearchStringResult(query="query2", chunks=[D, E])
            Query 3: SearchStringResult(query="query3", chunks=[F, G, H, I])

        Output (interleaved by position, then deduplicated):
            [
                SearchStringResult(query="query1", chunks=[A]),  # pos 0, query 1
                SearchStringResult(query="query2", chunks=[D]),  # pos 0, query 2
                SearchStringResult(query="query3", chunks=[F]),  # pos 0, query 3
                SearchStringResult(query="query1", chunks=[B]),  # pos 1, query 1
                SearchStringResult(query="query2", chunks=[E]),  # pos 1, query 2
                SearchStringResult(query="query3", chunks=[G]),  # pos 1, query 3
                SearchStringResult(query="query1", chunks=[C]),  # pos 2, query 1
                SearchStringResult(query="query3", chunks=[H]),  # pos 2, query 3
                SearchStringResult(query="query3", chunks=[I]),  # pos 3, query 3
            ]
    """
    if not search_results:
        return []

    max_chunks = max(len(result.chunks) for result in search_results)
    interleaved_search_results: list[SearchStringResult] = [
        SearchStringResult(query=result.query, chunks=[result.chunks[i]])
        for i in range(max_chunks)
        for result in search_results
        if i < len(result.chunks)
    ]

    return _deduplicate_search_results(interleaved_search_results)


def _deduplicate_search_results(
    search_results: list[SearchStringResult],
) -> list[SearchStringResult]:
    """
    Remove duplicate chunks from the search results based on their `chunk_id`.

    This function preserves the order of occurrences, keeping the first occurrence
    of each unique `chunk_id`. If a chunk has no `chunk_id`, it will be ignored.
    Duplicate chunks share the same `chunk_id`.

    Args:
        search_results (list[SearchStringResult]): A list of search results, where each
            result contains chunks with potential duplicate `chunk_id`s.

    Returns:
        list[SearchStringResult]: A deduplicated list of search results with unique `chunk_id` chunks.
    """
    seen_chunk_ids: set[str] = set()
    deduplicated_search_results: list[SearchStringResult] = []

    counter_chunks = 0
    for result in search_results:
        for chunk in result.chunks:
            if chunk.chunk_id and chunk.chunk_id not in seen_chunk_ids:
                counter_chunks += 1
                seen_chunk_ids.add(chunk.chunk_id)
                deduplicated_search_results.append(
                    SearchStringResult(query=result.query, chunks=[chunk])
                )

    if removed := counter_chunks - len(deduplicated_search_results):
        _LOGGER.info(
            f"Removed {removed} duplicate chunks ({len(deduplicated_search_results)}/{counter_chunks} unique)"
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

    if chunk.metadata is None:
        return chunk

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
