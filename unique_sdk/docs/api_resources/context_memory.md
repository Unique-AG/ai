# Context Memory API

The Context Memory API retrieves and updates the persistent context memory associated with the current user.

## Overview

Context memory stores a user-specific document that assistants can use across conversations. Each user has one context memory resource containing:

- The memory scope and content identifiers
- The stored document
- The last update timestamp

## Methods

??? example "`unique_sdk.ContextMemory.retrieve` - Retrieve context memory"

    Retrieve the context memory for the current user.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier

    **Returns:**

    Returns a [`ContextMemory`](#contextmemory) object.

    **Example:**

    ```python
    memory = unique_sdk.ContextMemory.retrieve(
        user_id=user_id,
        company_id=company_id,
    )

    print(memory.document)
    ```

    A missing context memory results in a `404 Not Found` API error.

??? example "`unique_sdk.ContextMemory.modify` - Update context memory"

    Replace the context memory document for the current user.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `document` (str, required) - New context memory document. An empty string clears the document.

    **Returns:**

    Returns the updated [`ContextMemory`](#contextmemory) object.

    **Example - Update memory:**

    ```python
    memory = unique_sdk.ContextMemory.modify(
        user_id=user_id,
        company_id=company_id,
        document="The user prefers concise answers in English.",
    )
    ```

    **Example - Clear memory:**

    ```python
    memory = unique_sdk.ContextMemory.modify(
        user_id=user_id,
        company_id=company_id,
        document="",
    )
    ```

## Async Methods

Both methods have async variants with an `_async` suffix:

- `retrieve_async`
- `modify_async`

```python
memory = await unique_sdk.ContextMemory.modify_async(
    user_id=user_id,
    company_id=company_id,
    document="The user prefers concise answers in English.",
)
```

## Return Types

#### ContextMemory {#contextmemory}

??? note "The `ContextMemory` object represents a user's persistent context memory"

    **Fields:**

    - `scopeId` (str) - Scope containing the context memory
    - `contentId` (str) - Content identifier of the stored memory
    - `document` (str) - Context memory document
    - `updatedAt` (str) - Last update timestamp in ISO 8601 format
    - `object` (Literal["context-memory"]) - Object type identifier

    **Returned by:** `ContextMemory.retrieve()`, `ContextMemory.modify()`

## Related Resources

- [Short Term Memory API](short_term_memory.md) - Store temporary chat and message data
- [Message API](message.md) - Create and manage chat messages
