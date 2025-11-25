# SearchString API

The SearchString API transforms and optimizes user queries for better search results by adding conversational context and translating to English.

## Overview

User messages are often suboptimal for vector or full-text search, especially in ongoing conversations where context is implied. This API enhances queries by:

- Adding conversational context from chat history
- Translating non-English queries to English
- Expanding vague references with specific details
- Creating optimal search strings for knowledge base queries

## Methods

??? example "`unique_sdk.SearchString.create` - Transform and optimize queries"

    Transform a user prompt into an optimized search string.

    **Parameters:**

    - `prompt` (str, required) - User's original query text
    - `chatId` (str, optional) - Chat ID to include conversation context for better results
    - `messages` (List[HistoryMessage], optional) - Explicit message history for context. See [`HistoryMessage`](#historymessage) for structure.
    - `languageModel` (Literal["AZURE_GPT_4_0613", "AZURE_GPT_4_32K_0613", "AZURE_GPT_4_TURBO_1106"], optional) - Language model to use for transformation

    **Returns:**

    Returns a [`SearchString`](#searchstring) object.

    **Example - Basic Usage:**

    ```python
    search_string = unique_sdk.SearchString.create(
        user_id=user_id,
        company_id=company_id,
        prompt="Was ist der Sinn des Lebens?",  # German query
    )
    ```

    **Example - With Chat Context:**

    ```python
    # Conversation context:
    # User: "Tell me about The Hitchhiker's Guide to the Galaxy"
    # Assistant: "It's a science fiction comedy series..."
    # User: "Who is the author?"

    search_string = unique_sdk.SearchString.create(
        user_id=user_id,
        company_id=company_id,
        prompt="Who is the author?",  # Vague without context
        chatId=chat_id
    )
    ```

    **Example - With Explicit Message History:**

    ```python
    search_string = unique_sdk.SearchString.create(
        user_id=user_id,
        company_id=company_id,
        prompt="What are the main themes?",
        messages=[
            {"role": "user", "content": "Tell me about 1984"},
            {"role": "assistant", "content": "1984 is a dystopian novel by George Orwell..."},
            {"role": "user", "content": "What are the main themes?"}
        ]
    )
    ```

## Input Types

#### HistoryMessage {#historymessage}

??? note "The `HistoryMessage` type defines a message in the conversation history"

    **Fields:**

    - `role` (Literal["system", "user", "assistant"], required) - Message role
    - `text` (str, required) - Message text content

    **Used in:** `SearchString.create()` `messages` parameter

## Related Resources

- [Search API](search.md) - Perform searches with enhanced queries
- [Chat History Utility](../sdk.md#chat-history) - Manage conversation context
- [Message API](message.md) - Access chat messages for context

