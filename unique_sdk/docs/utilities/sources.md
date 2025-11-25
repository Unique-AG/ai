# Sources Utility

Helper functions for processing and formatting search results for use in AI completions.

## Overview

The Sources utilities help you:

- Merge duplicate search results from the same document
- Sort results by document order
- Format source references
- Clean up document markers

## Methods

??? example "`unique_sdk.utils.sources.merge_sources` - Merge duplicate sources"

    Merges multiple search results from the same document, removing redundant markers and combining text chunks.

    **Parameters:**

    - `searchContext` (required) - List of search result objects with `id` and `text` keys

    **Returns:**

    - List of merged search result objects

    **How it works:**

    - Groups results by document `id`
    - Sorts chunks by `order` within each document
    - Merges text from multiple chunks
    - Removes document/info markers from subsequent chunks
    - Generates page number postfixes

    **Example:**

    ```python
    from unique_sdk.utils.sources import merge_sources
    import unique_sdk

    # Perform search
    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString="API documentation",
        searchType="COMBINED",
        limit=50
    )

    # Merge duplicate sources
    merged_results = merge_sources(search.data)

    # Now each document appears once with merged text
    for result in merged_results:
        print(result)
    ```

??? example "`unique_sdk.utils.sources.sort_sources` - Sort by document order"

    Sorts search results by their order of appearance in the original documents.

    **Parameters:**

    - `searchContext` (required) - List of search result objects

    **Returns:**

    - List of sorted search result objects

    **Example:**

    ```python
    from unique_sdk.utils.sources import sort_sources
    import unique_sdk

    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString="project timeline",
        searchType="COMBINED",
        limit=30
    )

    # Sort by document order
    sorted_results = sort_sources(search.data)

    # Results are now in document order
    for result in sorted_results:
        print(result)
    ```

## Best Practices

??? example "Process Sources in Order"

    ```python
    # Recommended: Merge first, then sort
    merged = merge_sources(search.data)
    sorted_results = sort_sources(merged)

    # This ensures:
    # 1. Duplicate documents are combined
    # 2. Results are in document order
    # 3. Page numbers are properly formatted
    ```

## Related Resources

- [Search API](../api_resources/search.md) - Get search results to process
- [Token Management](token.md) - Manage token limits for sources
- [ChatCompletion API](../api_resources/chat_completion.md) - Use sources in completions

