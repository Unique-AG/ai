import unique_sdk

from unique_toolkit.content.schemas import ContentChunk, SearchResult


def from_searches_to_content_chunks(searches: list[unique_sdk.Search]):
    """
    Maps unique_sdk search results to ContentChunk objects.

    Args:
        searches: The unique_sdk.Search objects.

    Returns:
        list[ContentChunk]: The ContentChunk objects
    """
    return [ContentChunk(**search) for search in searches]


def from_content_chunks_to_search_results(content_chunks: list[ContentChunk]):
    """
    Maps ContentChunk objects to unique_sdk search results.

    Args:
        content_chunks: The ContentChunk objects.

    Returns:
        list[unique_sdk.Search]: The unique_sdk.Search objects.
    """
    return [
        SearchResult(
            id=chunk.id,
            chunkId=chunk.chunk_id,  # type: ignore
            key=chunk.key,  # type: ignore
            title=chunk.title,  # type: ignore
            url=chunk.url,  # type: ignore
            text=chunk.text,
            startPage=chunk.start_page,
            endPage=chunk.end_page,
            order=chunk.order,
            object=chunk.object,
        )
        for chunk in content_chunks
    ]


def from_search_results_to_content_chunks(search_results: list[SearchResult]):
    """
    Maps SearchResults objects to ContentChunk objects.

    Args:
        search_results: The SearchResult objects.

    Returns:
        list[ContentChunk]: The ContentChunk objects.
    """

    return [ContentChunk(**result.model_dump()) for result in search_results]
