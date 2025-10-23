import logging

from unique_internal_search.service import SearchStringResult

_LOGGER = logging.getLogger(__name__)


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
