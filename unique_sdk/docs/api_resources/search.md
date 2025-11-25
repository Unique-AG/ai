# Search API

The Search API enables vector and full-text search across the Unique AI knowledge base for Retrieval-Augmented Generation (RAG).

## Overview

Perform semantic search with support for:

- Vector search
- Combined vector + full-text search
- Metadata filtering with UniqueQL
- Reranking
- Score thresholds
- Multi-scope search

## Methods

??? example "`unique_sdk.Search.create` - Search the knowledge base"

    Search the knowledge base with various filtering and ranking options.

    **Search Types:**

    - `VECTOR` - Semantic vector search
    - `COMBINED` - Vector + full-text search for enhanced precision

    **Parameters:**

    - `searchString` (str, required) - Query text to search for
    - `searchType` (Literal["VECTOR", "COMBINED"], required) - Search mode
    - `chatId` (str, optional) - Include chat documents in search scope
    - `scopeIds` (List[str], optional) - List of scope IDs to search within
    - `chatOnly` (bool, optional) - Restrict search to chat documents only
    - `limit` (int, optional) - Maximum number of results (default: 20, max: 1000)
    - `page` (int, optional) - Page number for pagination (default: 1)
    - `scoreThreshold` (float, optional) - Minimum similarity score (recommended: 0)
    - `language` (str, optional) - Language for full-text search (e.g., "English")
    - `reranker` (Dict[str, Any], optional) - Reranker configuration (e.g., `{"deploymentName": "my_deployment"}`)
    - `metaDataFilter` (Dict[str, Any], optional) - UniqueQL metadata filter
    - `contentIds` (List[str], optional) - Filter search to specific content IDs

    **Returns:**

    Returns a list of [`Search`](#search) objects.

    **Example - Basic Search:**

    ```python
    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        searchString="What is the meaning of life?",
        searchType="VECTOR",
        limit=20,
        scoreThreshold=0
    )
    ```

    **Example - Combined Search with Filtering:**

    ```python
    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString="quarterly financial performance",
        searchType="COMBINED",
        scopeIds=["scope_abc123", "scope_def456"],
        language="English",
        limit=50,
        page=1,
        scoreThreshold=0.7,
        reranker={"deploymentName": "my_deployment"}
    )
    ```

    **Example - Search with Metadata Filter:**

    ```python
    from unique_sdk import UQLOperator, UQLCombinator

    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString="project updates",
        searchType="COMBINED",
        metaDataFilter={
            UQLCombinator.AND: [
                {
                    "path": ["year"],
                    "operator": UQLOperator.EQUALS,
                    "value": "2024"
                },
                {
                    "path": ["department"],
                    "operator": UQLOperator.CONTAINS,
                    "value": "engineering"
                }
            ]
        },
        limit=30
    )
    ```

    **Example - Chat-Only Search:**

    ```python
    # Search only within uploaded chat documents
    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        searchString="contract terms",
        searchType="VECTOR",
        chatOnly=True,
        limit=10
    )
    ```

## Return Types

#### Search {#search}

??? note "The `Search` object represents a single search result"

    **Fields:**

    - `id` (str) - Unique search result identifier
    - `chunkId` (str) - Chunk identifier within the document
    - `text` (str) - Chunk text content
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)
    - `url` (str | None) - Content URL
    - `title` (str | None) - Document title
    - `key` (str | None) - File key/name with page numbers (e.g., "document.pdf : 5,6,7")
    - `order` (int) - Chunk order in document
    - `startPage` (int) - Starting page number
    - `endPage` (int) - Ending page number
    - `metadata` (Dict[str, Any] | None) - Custom metadata dictionary
    - `score` (float, optional) - Similarity score (may be present in API response)

    **Returned by:** `Search.create()`

## Best Practices

??? example "Use Combined Search for Better Results"

    ```python
    # Combined search is usually better than vector-only
    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString=query,
        searchType="COMBINED",  # Recommended
        scoreThreshold=0  # Include all results, let score guide ranking
    )
    ```

??? example "Enhance Queries with Context"

    ```python
    # Use SearchString API to improve queries
    from unique_sdk import SearchString

    # Transform user query with chat context
    enhanced = SearchString.create(
        user_id=user_id,
        company_id=company_id,
        prompt="Who is the author?",  # Vague query
        chat_id=chat_id  # Adds context from conversation
    )

    # Now search with enhanced query
    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString=enhanced.searchString,  # "Who is the author of Hitchhiker's Guide?"
        searchType="VECTOR"
    )
    ```

## Related Resources

- [SearchString API](search_string.md) - Enhance queries with context
- [Content API](content.md) - Manage searchable content
- [UniqueQL](../sdk.md#uniqueql) - Advanced filtering
- [Token Utils](../sdk.md#token) - Optimize token usage

