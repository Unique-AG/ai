# Message API

The Message API allows you to create, retrieve, update, and delete chat messages.

## Overview

Manage chat messages and integrate with the Unique AI chat system. Includes support for streaming responses and message events.

## Methods

??? example "`unique_sdk.Message.list` - Retrieve all messages"

    Retrieve all messages for a chat.

    **Parameters:**

    - `chatId` (str, required) - Chat ID to retrieve messages from

    **Returns:**

    Returns a [`ListObject`](#listobject) containing [`Message`](#message) objects.

    **Example:**

    ```python
    messages = unique_sdk.Message.list(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
    )
    ```

??? example "`unique_sdk.Message.retrieve` - Get a single message"

    Get a single message by ID.

    **Parameters:**

    - `id` (str, required) - Message ID to retrieve
    - `chatId` (str, required) - Chat ID containing the message

    **Returns:**

    Returns a [`Message`](#message) object.

    **Example:**

    ```python
    message = unique_sdk.Message.retrieve(
        user_id=user_id,
        company_id=company_id,
        id=message_id,
        chatId=chat_id,
    )
    ```

??? example "`unique_sdk.Message.create` - Create a new message"

    Create a new message in a chat.

    **Parameters:**

    - `chatId` (str, required) - Chat ID to create message in
    - `assistantId` (str, required) - Assistant ID associated with the message
    - `role` (Literal["ASSISTANT"], required) - Message role (must be "ASSISTANT")
    - `text` (str, optional) - Message text content
    - `references` (List[Reference], optional) - List of source references. See [`Message.Reference`](#messagereference) for structure.
    - `debugInfo` (Dict[str, Any], optional) - Debug information dictionary
    - `completedAt` (datetime, optional) - Completion timestamp

    **Returns:**

    Returns a [`Message`](#message) object.

    **Example:**

    ```python
    message = unique_sdk.Message.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        assistantId=assistant_id,
        text="Hello.",
        role="ASSISTANT",  # or "USER"
    )
    ```

??? example "`unique_sdk.Message.create_event` - Create a message event"

    !!! info "Compatibility"
        Compatible with release >.42

    Create a message event to update the chat UI without database persistence. Useful for custom streaming.

    !!! warning
        This only updates the UI, not the database.

    **Parameters:**

    - `messageId` (str, required) - Message ID to update
    - `chatId` (str, required) - Chat ID containing the message
    - `text` (str, optional) - Updated message text
    - `originalText` (str, optional) - Original message text
    - `references` (List[Reference], optional) - List of source references. See [`Message.Reference`](#messagereference) for structure.
    - `gptRequest` (Dict[str, Any], optional) - GPT request data
    - `debugInfo` (Dict[str, Any], optional) - Debug information dictionary
    - `completedAt` (datetime, optional) - Completion timestamp

    **Returns:**

    Returns a [`Message`](#message) object.

    **Example:**

    ```python
    message = unique_sdk.Message.create_event(
        user_id=user_id,
        company_id=company_id,
        messageId="msg_l4ushn85yqbewpf6tllh2cl7",
        chatId="chat_kc8p3kgkn7393qhgmv5js5nt",
        text="Hello.",                  # optional
        originalText="Hello.",          # optional
        references=[],                  # optional
        gptRequest={},                  # optional
        debugInfo={"hello": "test"},    # optional
    )
    ```

??? example "`unique_sdk.Message.modify` - Update an existing message"

    Update an existing message.

    !!! tip
        Only modify `debugInfo` on user messages - it's only displayed there in the frontend.

    **Parameters:**

    - `id` (str, required) - Message ID to update
    - `chatId` (str, required) - Chat ID containing the message
    - `text` (str, optional) - Updated message text
    - `references` (List[Reference], optional) - List of source references. See [`Message.Reference`](#messagereference) for structure.
    - `debugInfo` (Dict[str, Any], optional) - Debug information dictionary
    - `completedAt` (datetime, optional) - Completion timestamp

    **Returns:**

    Returns a [`Message`](#message) object.

    **Example:**

    ```python
    message = unique_sdk.Message.modify(
        user_id=user_id,
        company_id=company_id,
        id=message_id,
        chatId=chat_id,
        text="Updated message text"
    )
    ```

??? example "`unique_sdk.Message.delete` - Delete a message"

    Delete a message from a chat.

    !!! warning
        Message deletion doesn't auto-sync with UI. Users must refresh to see changes.

    **Parameters:**

    - `message_id` (str, required) - Message ID to delete (positional argument)
    - `chatId` (str, required) - Chat ID containing the message

    **Returns:**

    Returns a [`Message`](#message) object.

    **Example:**

    ```python
    message = unique_sdk.Message.delete(
        message_id,
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
    )
    ```

## Streaming Methods

??? example "`unique_sdk.Integrated.chat_stream_completion` - Stream AI response (using ChatCompletions API)"

    Stream an AI-generated response to the chat frontend with automatic source reference handling, using ChatCompletions API.

    **Source References:** `[source0]` in the stream is automatically converted to `<sup>1</sup>` with proper reference linking.

    ```python
    unique_sdk.Integrated.chat_stream_completion(
        user_id=userId,
        company_id=companyId,
        assistantMessageId=assistantMessageId,
        userMessageId=userMessageId,
        messages=[
            {
                "role": "system",
                "content": "be friendly and helpful"
            },
            {
                "role": "user",
                "content": "hello"
            }
        ],
        chatId=chatId,
        searchContext=[
            {
                "id": "ref_qavsg0dcl5cbfwm1fvgogrvo",
                "chunkId": "0",
                "key": "some reference.pdf : 8,9,10,11",
                "sequenceNumber": 1,
                "url": "unique://content/cont_p8n339trfsf99oc9f36rn4wf"
            }
        ],  # optional
        debugInfo={"hello": "test"},  # optional
        startText="I want to tell you about: ",  # optional
        model="AZURE_GPT_4_32K_0613",  # optional
        timeout=8000,  # optional in ms
        options={"temperature": 0.5}  # optional
    )
    ```

??? example "`unique_sdk.Integrated.responses_stream` - Stream AI response (using Responses API)"

    Stream an AI-generated response to the chat frontend with automatic source reference handling, using Responses API.

    ```python
    unique_sdk.Integrated.responses_stream(
        user_id=userId,
        company_id=companyId,
        model="AZURE_o3_2025_0416",
        assistantMessageId=assistantMessageId,
        userMessageId=userMessageId,
        input="Tell me about the curious case of neural text degeneration",
        chatId=chatId,
    )
    ```

## Input Types

#### Message.Reference {#messagereference}

??? note "The `Message.Reference` type defines source reference information for messages"

    **Fields:**

    - `name` (str, required) - Reference name/title
    - `description` (str, optional) - Reference description
    - `url` (str, optional) - Reference URL
    - `sequenceNumber` (int, required) - Sequence number for ordering references
    - `originalIndex` (list[int], optional) - Original index positions
    - `sourceId` (str, required) - Source identifier
    - `source` (str, required) - Source name/path

    **Used in:** `Message.create()`, `Message.modify()`, `Message.create_event()`

## Return Types

#### Message {#message}

??? note "The `Message` object represents a chat message"

    **Fields:**

    - `id` (str) - Unique message identifier
    - `chatId` (str) - Chat ID containing the message
    - `text` (str | None) - Message text content
    - `role` (Literal["SYSTEM", "USER", "ASSISTANT"]) - Message role
    - `gptRequest` (Dict[str, Any] | None) - GPT request data
    - `debugInfo` (Dict[str, Any] | None) - Debug information dictionary
    - `references` (List[Reference] | None) - List of source references
    - `completedAt` (datetime | None) - Completion timestamp
    - `createdAt` (str | None) - Creation timestamp (ISO 8601)
    - `updatedAt` (str | None) - Last update timestamp (ISO 8601)

    **Returned by:** `Message.list()`, `Message.retrieve()`, `Message.create()`, `Message.modify()`, `Message.delete()`, `Message.create_event()`

#### ListObject {#listobject}

??? note "The `ListObject` type represents a paginated list of messages"

    **Fields:**

    - `data` (List[Message]) - List of message objects
    - `has_more` (bool) - Whether there are more items to retrieve
    - `object` (str) - Object type identifier (always "list")

    **Returned by:** `Message.list()`

## Related Resources

- [Message Log API](message_log.md) - Track message execution steps
- [Message Execution API](message_execution.md) - Manage long-running message operations
- [Message Assessment API](message_assessment.md) - Evaluate message quality
- [Chat History Utility](../utilities/chat_history.md) - Manage conversation history

