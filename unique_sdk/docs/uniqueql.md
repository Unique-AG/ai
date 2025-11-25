# UniqueQL Query Language

UniqueQL is an advanced query language designed to enhance search capabilities within the Unique AI platform. It enables powerful metadata filtering for vector search, full-text search, and combined search modes.

## Overview

UniqueQL allows you to filter search results by metadata attributes such as:
- File names and paths
- URLs and document sources
- Dates and timestamps
- Custom metadata fields
- Folder hierarchies
- Document properties

The query language is versatile and can be translated into different query formats for various database systems, including PostgreSQL and Qdrant.

## Importing UniqueQL

```python
from unique_sdk import UQLOperator, UQLCombinator
```

## Query Structure

A UniqueQL query consists of three components:

1. **Path**: Specifies the metadata attribute to filter (e.g., `["title"]`, `["year"]`, `["folderIdPath"]`)
2. **Operator**: Defines the type of comparison (e.g., `EQUALS`, `CONTAINS`, `GREATER_THAN`)
3. **Value**: Provides the criteria for the filter

## Operators

### Comparison Operators

??? example "EQUALS - Exact match"

    ```python
    {
        "path": ["year"],
        "operator": UQLOperator.EQUALS,
        "value": "2024"
    }
    ```

??? example "NOT_EQUALS - Exclude value"

    ```python
    {
        "path": ["status"],
        "operator": UQLOperator.NOT_EQUALS,
        "value": "archived"
    }
    ```

??? example "CONTAINS - Substring match"

    ```python
    {
        "path": ["title"],
        "operator": UQLOperator.CONTAINS,
        "value": "report"
    }
    ```

??? example "NOT_CONTAINS - Exclude substring"

    ```python
    {
        "path": ["title"],
        "operator": UQLOperator.NOT_CONTAINS,
        "value": "draft"
    }
    ```

### Numeric and Date Operators

These operators work with both numbers and dates (ISO 8601 format).

??? example "GREATER_THAN - Numeric comparison"

    ```python
    {
        "path": ["size"],
        "operator": UQLOperator.GREATER_THAN,
        "value": 1000
    }
    ```

??? example "GREATER_THAN - Date comparison"

    ```python
    {
        "path": ["createdAt"],
        "operator": UQLOperator.GREATER_THAN,
        "value": "2024-01-01T00:00:00Z"
    }
    ```

??? example "LESS_THAN_OR_EQUAL - Numeric range filtering"

    ```python
    {
        "path": ["pageCount"],
        "operator": UQLOperator.LESS_THAN_OR_EQUAL,
        "value": 50
    }
    ```

??? example "LESS_THAN - Date filtering"

    ```python
    {
        "path": ["updatedAt"],
        "operator": UQLOperator.LESS_THAN,
        "value": "2024-12-31T23:59:59Z"
    }
    ```

### List Operators

??? example "IN - Match any value in list"

    ```python
    {
        "path": ["department"],
        "operator": UQLOperator.IN,
        "value": ["Engineering", "Sales", "Marketing"]
    }
    ```

??? example "NOT_IN - Exclude values"

    ```python
    {
        "path": ["category"],
        "operator": UQLOperator.NOT_IN,
        "value": ["internal", "draft"]
    }
    ```

### Null/Empty Operators

??? example "IS_NOT_NULL - Exclude null values"

    ```python
    {
        "path": ["author"],
        "operator": UQLOperator.IS_NOT_NULL,
        "value": None
    }
    ```

??? example "IS_NOT_EMPTY - Exclude empty values"

    ```python
    {
        "path": ["description"],
        "operator": UQLOperator.IS_NOT_EMPTY,
        "value": None
    }
    ```

## Combinators

Use `AND` and `OR` combinators to build complex queries:

??? example "AND - All conditions must match"

    ```python
    {
        UQLCombinator.AND: [
            {
                "path": ["year"],
                "operator": UQLOperator.EQUALS,
                "value": "2024"
            },
            {
                "path": ["department"],
                "operator": UQLOperator.EQUALS,
                "value": "Engineering"
            }
        ]
    }
    ```

??? example "OR - Any condition can match"

    ```python
    {
        UQLCombinator.OR: [
            {
                "path": ["status"],
                "operator": UQLOperator.EQUALS,
                "value": "published"
            },
            {
                "path": ["status"],
                "operator": UQLOperator.EQUALS,
                "value": "reviewed"
            }
        ]
    }
    ```

## Complex Queries

??? example "Nested Queries - Filter nested metadata structures"

    Use `NESTED` operator for filtering within nested metadata structures:

    ```python
    from unique_sdk import UQLOperator, UQLCombinator

    metadata_filter = {
        "path": ['diet', '*'],
        "operator": UQLOperator.NESTED,
        "value": {
            UQLCombinator.OR: [
                {
                    UQLCombinator.OR: [
                        {
                            "path": ['food'],
                            "operator": UQLOperator.EQUALS,
                            "value": "meat",
                        },
                        {
                            "path": ['food'],
                            "operator": UQLOperator.EQUALS,
                            "value": "vegetables",
                        },
                    ],
                },
                {
                    "path": ['likes'],
                    "operator": UQLOperator.EQUALS,
                    "value": True,
                },
            ],
        },
    }
    ```

??? example "Combining AND and OR - Complex filter logic"

    ```python
    metadata_filter = {
        UQLCombinator.AND: [
            {
                "path": ["title"],
                "operator": UQLOperator.CONTAINS,
                "value": "report"
            },
            {
                UQLCombinator.OR: [
                    {
                        "path": ["year"],
                        "operator": UQLOperator.EQUALS,
                        "value": "2024"
                    },
                    {
                        "path": ["year"],
                        "operator": UQLOperator.EQUALS,
                        "value": "2023"
                    }
                ]
            }
        ]
    }
    ```

## Common Use Cases

??? example "Filter by Folder Path"

    ```python
    metadata_filter = {
        "path": ["folderIdPath"],
        "operator": UQLOperator.CONTAINS,
        "value": "uniquepathid://scope_engineering_docs"
    }

    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString="API documentation",
        searchType="COMBINED",
        metaDataFilter=metadata_filter
    )
    ```

??? example "Filter by Date Range"

    Date operators work with ISO 8601 date strings. You can use dates with or without time:

    ```python
    # Date range filter
    metadata_filter = {
        UQLCombinator.AND: [
            {
                "path": ["createdAt"],
                "operator": UQLOperator.GREATER_THAN_OR_EQUAL,
                "value": "2024-01-01"  # Date only
            },
            {
                "path": ["createdAt"],
                "operator": UQLOperator.LESS_THAN_OR_EQUAL,
                "value": "2024-12-31"  # Date only
            }
        ]
    }

    # Or with full timestamp
    metadata_filter = {
        UQLCombinator.AND: [
            {
                "path": ["updatedAt"],
                "operator": UQLOperator.GREATER_THAN,
                "value": "2024-01-01T00:00:00Z"  # Full ISO 8601
            },
            {
                "path": ["updatedAt"],
                "operator": UQLOperator.LESS_THAN,
                "value": "2024-12-31T23:59:59Z"
            }
        ]
    }
    ```

??? example "Filter by Multiple Departments"

    ```python
    metadata_filter = {
        "path": ["department"],
        "operator": UQLOperator.IN,
        "value": ["Engineering", "Product", "Design"]
    }
    ```

??? example "Exclude Specific Documents"

    ```python
    metadata_filter = {
        UQLCombinator.AND: [
            {
                "path": ["status"],
                "operator": UQLOperator.EQUALS,
                "value": "published"
            },
            {
                "path": ["category"],
                "operator": UQLOperator.NOT_IN,
                "value": ["internal", "draft"]
            }
        ]
    }
    ```

## Using with Search API

??? example "Pass the metadata filter to the `Search.create` method"

    ```python
    from unique_sdk import UQLOperator, UQLCombinator

    # Build filter
    metadata_filter = {
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
    }

    # Use in search
    search_results = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        searchString="project updates",
        searchType="COMBINED",
        metaDataFilter=metadata_filter,
        limit=30
    )
    ```

## Using with Content API

??? example "UniqueQL filters can also be used with the Content API"

    ```python
    content_info_result = unique_sdk.Content.get_infos(
        user_id=user_id,
        company_id=company_id,
        metadataFilter={
            "or": [
                {
                    "and": [
                        {
                            "operator": "contains",
                            "path": ["folderIdPath"],
                            "value": "uniquepathid://scope_abcdibgznc4bkdcx120zm5d"
                        },
                        {
                            "operator": "contains",
                            "path": ["title"],
                            "value": "ai"
                        }
                    ]
                }
            ]
        },
        skip=0,
        take=3,
    )
    ```

## Best Practices

### Combine Filters Efficiently

??? example "Use `AND` for restrictive filters and `OR` for inclusive filters"

    ```python
    # Restrictive: Must match all
    {
        UQLCombinator.AND: [
            {"path": ["year"], "operator": UQLOperator.EQUALS, "value": "2024"},
            {"path": ["status"], "operator": UQLOperator.EQUALS, "value": "published"}
        ]
    }

    # Inclusive: Match any
    {
        UQLCombinator.OR: [
            {"path": ["department"], "operator": UQLOperator.EQUALS, "value": "Engineering"},
            {"path": ["department"], "operator": UQLOperator.EQUALS, "value": "Product"}
        ]
    }
    ```

### Test Filters Incrementally

??? example "Build complex filters step by step"

    ```python
    # Start simple
    filter1 = {
        "path": ["year"],
        "operator": UQLOperator.EQUALS,
        "value": "2024"
    }

    # Add more conditions
    filter2 = {
        UQLCombinator.AND: [
            filter1,
            {
                "path": ["status"],
                "operator": UQLOperator.EQUALS,
                "value": "published"
            }
        ]
    }
    ```

## Complete Operator Reference

| Operator | Description | Example Value Types |
|----------|-------------|---------------------|
| `EQUALS` | Exact match | String, Number, Boolean |
| `NOT_EQUALS` | Exclude exact match | String, Number, Boolean |
| `CONTAINS` | Substring match | String |
| `NOT_CONTAINS` | Exclude substring | String |
| `GREATER_THAN` | Greater than | Number, Date (ISO 8601) |
| `GREATER_THAN_OR_EQUAL` | Greater than or equal | Number, Date (ISO 8601) |
| `LESS_THAN` | Less than | Number, Date (ISO 8601) |
| `LESS_THAN_OR_EQUAL` | Less than or equal | Number, Date (ISO 8601) |
| `IN` | Match any value in list | Array |
| `NOT_IN` | Exclude values in list | Array |
| `IS_NULL` | Value is null | None |
| `IS_NOT_NULL` | Value is not null | None |
| `IS_EMPTY` | Value is empty | None |
| `IS_NOT_EMPTY` | Value is not empty | None |
| `NESTED` | Filter nested structures | Object |

## Next Steps

Now that you understand UniqueQL:

1. **[Try Search with Filters](api_resources/search.md)** - Use UniqueQL in search queries
2. **[Explore Content API](api_resources/content.md)** - Filter content with metadata
3. **[See Tutorials](../tutorials/get_contents.md)** - View rule-based search tutorial
4. **[Read Full Documentation](https://unique-ch.atlassian.net/wiki/x/coAXHQ)** - Official UniqueQL documentation

## Related Resources

- [Search API](api_resources/search.md) - Use UniqueQL filters in search
- [Content API](api_resources/content.md) - Filter content with metadata
- [Folder API](api_resources/folder.md) - Filter by folder paths
- [Space API](api_resources/space.md) - Use scope rules with UniqueQL
