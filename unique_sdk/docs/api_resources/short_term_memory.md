# Short Term Memory API

The Short Term Memory API provides temporary storage for data between chat rounds (up to 10,000 characters).

## Overview

Store small amounts of data temporarily for:

- Conversation state
- Search results
- User preferences
- Temporary calculations

**Capacity:** 10,000 characters per memory

## Methods

??? example "`unique_sdk.ShortTermMemory.create` - Store memory"

    Create or update a short-term memory.

    **Storage Options:**

    - By `chatId` - Store for entire chat
    - By `messageId` - Store for specific message

    **Parameters:**

    - `memoryName` (str, required) - Identifier for the memory
    - `data` (str, optional) - Data to store (max 10,000 characters)
    - `chatId` (str, optional) - Associate with chat
    - `messageId` (str, optional) - Associate with message

    **Returns:**

    Returns a [`ShortTermMemory`](#shorttermmemory) object.

    **Example:**

    ```python
    memory = unique_sdk.ShortTermMemory.create(
        user_id=user_id,
        company_id=company_id,
        data="user prefers detailed explanations",
        chatId="chat_x0xxtj89f7drjp4vmued3q",
        memoryName="user_preferences"
    )

    print(memory)
    ```

??? example "`unique_sdk.ShortTermMemory.find_latest` - Retrieve memory"

    Retrieve the most recent memory by name.

    **Parameters:**

    - `memoryName` (str, required) - Memory identifier to retrieve
    - `chatId` (str, optional) - Filter by chat ID
    - `messageId` (str, optional) - Filter by message ID

    **Returns:**

    Returns a [`ShortTermMemory`](#shorttermmemory) object.

    **Example:**

    ```python
    memory = unique_sdk.ShortTermMemory.find_latest(
        user_id=user_id,
        company_id=company_id,
        chatId="chat_x0xxtj89f7drjp4vmued3q",
        memoryName="user_preferences"
    )

    print(memory.data)
    ```

## Use Cases

??? example "Conversation Preferences"

    ```python
    def save_user_preference(chat_id, preference_key, preference_value):
        """Save user preferences for a chat."""
        
        # Load existing preferences
        try:
            memory = unique_sdk.ShortTermMemory.find_latest(
                user_id=user_id,
                company_id=company_id,
                chatId=chat_id,
                memoryName="preferences"
            )
            import json
            prefs = json.loads(memory.data)
        except:
            prefs = {}
        
        # Update preference
        prefs[preference_key] = preference_value
        
        # Save back
        unique_sdk.ShortTermMemory.create(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            memoryName="preferences",
            data=json.dumps(prefs)
        )

    # Usage
    save_user_preference(chat_id, "response_length", "detailed")
    save_user_preference(chat_id, "language", "english")
    ```

## Return Types

#### ShortTermMemory {#shorttermmemory}

??? note "The `ShortTermMemory` object represents a short-term memory entry"

    **Fields:**

    - `id` (str) - Unique memory identifier
    - `memoryName` (str) - Memory identifier/name
    - `chatId` (str | None) - Associated chat ID
    - `messageId` (str | None) - Associated message ID
    - `data` (str | None) - Stored data (max 10,000 characters)

    **Returned by:** `ShortTermMemory.create()`, `ShortTermMemory.find_latest()`

## Related Resources

- [Message API](message.md) - Associate memory with messages
- [Chat History Utility](../sdk.md#chat-history) - Long-term conversation history

