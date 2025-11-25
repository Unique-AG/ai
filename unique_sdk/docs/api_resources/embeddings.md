# Embeddings API

The Embeddings API converts text into vector embeddings for semantic search and similarity comparisons.

## Overview

Generate vector embeddings for text using Unique AI's embedding models.

## Methods

??? example "`unique_sdk.Embeddings.create` - Generate vector embeddings"

    Convert text strings into vector embeddings.

    **Parameters:**

    - `user_id` (required)
    - `company_id` (required)
    - `texts` (required) - Array of strings to embed

    **Example:**

    ```python
    result = unique_sdk.Embeddings.create(
        user_id=user_id,
        company_id=company_id,
        texts=["hello", "world", "embeddings"]
    )

    # Access embeddings
    for i, embedding in enumerate(result.embeddings):
        print(f"Text {i}: {len(embedding)} dimensions")
        print(f"First 5 values: {embedding[:5]}")
    ```

## Response Format

```python
{
    "embeddings": [
        [0.123, -0.456, 0.789, ...],  # Vector for first text
        [0.234, -0.567, 0.890, ...],  # Vector for second text
        ...
    ]
}
```

Each embedding is a list of floating-point numbers representing the text in vector space.

## Related Resources

- [Search API](search.md) - Built-in vector search
- [Content API](content.md) - Index documents automatically

