# Space API

The Space API manages conversational spaces (assistants) and their chats in Unique AI.

## Overview

Spaces are conversational assistants with configured tools, scope rules, and modules. Use this API to:

- Send messages to spaces
- Manage space chats
- Retrieve space configuration
- Access message history

## Methods

??? example "`unique_sdk.Space.create_message` - Send message in space"

    Send a message in a space. Creates a new chat if no `chatId` provided.

    **Parameters:**

    - `assistantId` (str, required) - Space/assistant ID
    - `text` (str, optional) - Message text
    - `chatId` (str, optional) - Continue existing chat or start new
    - `toolChoices` (List[str], optional) - List of tools to use (e.g., `["WebSearch", "InternalSearch"]`)
    - `scopeRules` (Dict[str, Any], optional) - UniqueQL filter for document scope

    **Returns:**

    Returns a [`Space.Message`](#spacemessage) object.

    **Example - New Chat:**

    ```python
    message = unique_sdk.Space.create_message(
        user_id=user_id,
        company_id=company_id,
        assistantId="assistant_abc123",
        text="Hello, how can you help me?",
        toolChoices=["WebSearch", "InternalSearch"]
    )

    chat_id = message.chatId  # Save for next message
    ```

    **Example - Continue Chat:**

    ```python
    message = unique_sdk.Space.create_message(
        user_id=user_id,
        company_id=company_id,
        chatId="chat_dejfhe729br398",  # Existing chat
        assistantId="assistant_abc123",
        text="Tell me more"
    )
    ```

    **Example - With Scope Rules:**

    ```python
    message = unique_sdk.Space.create_message(
        user_id=user_id,
        company_id=company_id,
        assistantId="assistant_abc123",
        text="Search our engineering docs",
        toolChoices=["InternalSearch"],
        scopeRules={
            "or": [
                {
                    "operator": "contains",
                    "path": ["folderIdPath"],
                    "value": "uniquepathid://scope_engineering_docs"
                }
            ]
        }
    )
    ```

??? example "`unique_sdk.Space.get_chat_messages` - Get paginated messages"

    !!! info "Compatibility"
        Compatible with release >.48

    Get paginated messages from a space chat.

    **Parameters:**

    - `chat_id` (str, required) - Chat ID to retrieve messages from
    - `skip` (int, optional) - Number of messages to skip (default: 0)
    - `take` (int, optional) - Number of messages to return (default: 10, max: 100)

    **Returns:**

    Returns a [`GetAllMessagesResponse`](#getallmessagesresponse) object.

    ```python
    messages = unique_sdk.Space.get_chat_messages(
        user_id=user_id,
        company_id=company_id,
        chat_id="chat_dejfhe729br398",
        skip=0,
        take=50
    )

    for msg in messages.data:
        print(f"{msg.role}: {msg.text}")
    ```

??? example "`unique_sdk.Space.get_latest_message` - Get most recent message"

    Get the most recent message in a space chat.

    **Parameters:**

    - `chat_id` (str, required) - Chat ID to get latest message from

    **Returns:**

    Returns a [`Space.Message`](#spacemessage) object.

    **Example:**

    ```python
    message = unique_sdk.Space.get_latest_message(
        user_id=user_id,
        company_id=company_id,
        chat_id="chat_dejfhe729br398"
    )

    print(f"Latest: {message.text}")
    ```

??? example "`unique_sdk.Space.get_space` - Get space configuration"

    !!! info "Compatibility"
        Compatible with release >.48

    Get detailed space configuration including modules and scope rules.

    **Parameters:**

    - `space_id` (str, required) - Space/assistant ID

    **Returns:**

    Returns a [`Space`](#space) object.

    **Example:**

    ```python
    space = unique_sdk.Space.get_space(
        user_id=user_id,
        company_id=company_id,
        space_id="assistant_hjcdga64bkcjnhu4"
    )

    print(f"Space: {space.name}")
    print(f"Modules: {space.modules}")
    print(f"Scope Rules: {space.scopeRules}")
    ```

??? example "`unique_sdk.Space.delete_chat` - Delete a chat"

    Delete a chat by ID.

    **Parameters:**

    - `chat_id` (str, required) - Chat ID to delete

    **Returns:**

    Returns a [`DeleteChatResponse`](#deletechatresponse) object.

    **Example:**

    ```python
    unique_sdk.Space.delete_chat(
        user_id=user_id,
        company_id=company_id,
        chat_id="chat_dejfhe729br398"
    )
    ```

## Use Cases

??? example "Chat Against File"

    ```python
    from unique_sdk.utils.chat_in_space import chat_against_file

    async def process_document(file_path):
        """Upload and chat with a document."""
        result = await chat_against_file(
            user_id=user_id,
            company_id=company_id,
            assistant_id="assistant_abc123",
            path_to_file=file_path,
            displayed_filename="report.pdf",
            mime_type="application/pdf",
            text="Summarize the key findings",
            should_delete_chat=True  # Clean up after
        )
        
        return result.text

    # Usage
    import asyncio
    summary = asyncio.run(process_document("/path/to/report.pdf"))
    ```

??? example "Wait for Response"

    ```python
    from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

    async def get_space_response(assistant_id, question):
        """Send message and wait for completion."""
        message = await send_message_and_wait_for_completion(
            user_id=user_id,
            company_id=company_id,
            assistant_id=assistant_id,
            text=question,
            tool_choices=["WebSearch", "InternalSearch"],
            poll_interval=2,  # Check every 2 seconds
            max_wait=120,  # Wait up to 2 minutes
            stop_condition="completedAt"  # Wait for full completion
        )
        
        return message.text

    # Usage
    import asyncio
    answer = asyncio.run(
        get_space_response(
            "assistant_abc123",
            "What are the latest developments in AI?"
        )
    )
    ```

??? example "Scoped Search"

    ```python
    def search_department_docs(assistant_id, query, department_scope):
        """Search specific department documents."""
        message = unique_sdk.Space.create_message(
            user_id=user_id,
            company_id=company_id,
            assistantId=assistant_id,
            text=query,
            toolChoices=["InternalSearch"],
            scopeRules={
                "or": [
                    {
                        "operator": "contains",
                        "path": ["folderIdPath"],
                        "value": f"uniquepathid://{department_scope}"
                    }
                ]
            }
        )
        
        return message

    # Search engineering docs only
    result = search_department_docs(
        "assistant_abc123",
        "API documentation",
        "scope_engineering_123"
    )
    ```

## Return Types

#### Space.Message {#spacemessage}

??? note "The `Space.Message` object represents a message in a space chat"

    **Fields:**

    - `id` (str) - Unique message identifier
    - `chatId` (str) - Chat ID containing the message
    - `text` (str | None) - Message text content
    - `originalText` (str | None) - Original message text before processing
    - `role` (Literal["SYSTEM", "USER", "ASSISTANT"]) - Message role
    - `debugInfo` (Dict[str, Any] | None) - Debug information dictionary
    - `completedAt` (str | None) - Completion timestamp (ISO 8601)
    - `createdAt` (str | None) - Creation timestamp (ISO 8601)
    - `updatedAt` (str | None) - Last update timestamp (ISO 8601)
    - `stoppedStreamingAt` (str | None) - When streaming stopped (ISO 8601)
    - `references` (List[Reference] | None) - List of source references. See [`Space.Reference`](#spacereference) for structure.
    - `assessment` (List[Assessment] | None) - List of message assessments. See [`Space.Assessment`](#spaceassessment) for structure.

    **Returned by:** `Space.create_message()`, `Space.get_latest_message()`

#### Space.Reference {#spacereference}

??? note "The `Space.Reference` type defines source reference information for messages"

    **Fields:**

    - `name` (str) - Reference name/title
    - `description` (str | None) - Reference description
    - `url` (str | None) - Reference URL
    - `sequenceNumber` (int) - Sequence number for ordering references
    - `originalIndex` (list[int] | None) - Original index positions
    - `sourceId` (str) - Source identifier
    - `source` (str) - Source name/path

    **Used in:** `Space.Message.references`

#### Space.Assessment {#spaceassessment}

??? note "The `Space.Assessment` type defines assessment information for messages"

    **Fields:**

    - `id` (str) - Unique assessment identifier
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)
    - `messageId` (str) - Associated message ID
    - `status` (str) - Assessment status
    - `explanation` (str | None) - Assessment explanation
    - `label` (str | None) - Assessment label
    - `type` (str | None) - Assessment type
    - `title` (str | None) - Assessment title
    - `companyId` (str) - Company ID
    - `userId` (str) - User ID
    - `isVisible` (bool) - Whether assessment is visible
    - `createdBy` (str | None) - Creator user ID

    **Used in:** `Space.Message.assessment`

#### GetAllMessagesResponse {#getallmessagesresponse}

??? note "The `GetAllMessagesResponse` object contains paginated messages"

    **Fields:**

    - `messages` (List[Space.Message]) - List of message objects
    - `totalCount` (int) - Total number of messages in chat

    **Returned by:** `Space.get_chat_messages()`

#### Space {#space}

??? note "The `Space` object represents a conversational space/assistant"

    **Fields:**

    - `id` (str) - Unique space identifier
    - `name` (str) - Space name
    - `defaultForCompanyId` (str | None) - Default company ID
    - `title` (str | None) - Space title
    - `subtitle` (str | None) - Space subtitle
    - `explanation` (str | None) - Space explanation
    - `alert` (str | None) - Alert message
    - `inputLimit` (int | None) - Input character limit
    - `inputPlaceholder` (str | None) - Input placeholder text
    - `chatUpload` (str) - Chat upload configuration
    - `goals` (List[str]) - List of space goals
    - `languageModel` (str | None) - Language model identifier
    - `fallbackModule` (str) - Fallback module identifier
    - `access` (List[str]) - Access control list
    - `isExternal` (bool) - Whether space is external
    - `isPinned` (bool) - Whether space is pinned
    - `uiType` (str) - UI type identifier
    - `settings` (Dict[str, Any] | None) - Space settings
    - `assistantMcpServers` (List[AssistantMcpServer]) - List of MCP servers. See [`Space.AssistantMcpServer`](#spaceassistantmcpserver) for structure.
    - `modules` (List[Module]) - List of configured modules. See [`Space.Module`](#spacemodule) for structure.
    - `scopeRules` (List[ScopeRule]) - List of scope rules. See [`Space.ScopeRule`](#spacescoperule) for structure.
    - `assistantAccess` (List[AssistantAccess]) - List of access controls. See [`Space.AssistantAccess`](#spaceassistantaccess) for structure.
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)

    **Returned by:** `Space.get_space()`

#### Space.AssistantMcpServer {#spaceassistantmcpserver}

??? note "The `Space.AssistantMcpServer` object represents an MCP server associated with a space"

    **Fields:**

    - `id` (str) - Unique MCP server association identifier
    - `name` (str) - MCP server name
    - `assistantId` (str) - Associated assistant/space ID
    - `mcpServerId` (str) - MCP server ID
    - `isEnabled` (bool) - Whether the MCP server is enabled
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)

    **Used in:** `Space.assistantMcpServers`

#### Space.Module {#spacemodule}

??? note "The `Space.Module` object represents a module configured for a space"

    **Fields:**

    - `id` (str) - Unique module identifier
    - `name` (str) - Module name
    - `description` (str | None) - Module description
    - `toolDefinition` (Dict[str, Any] | None) - Tool definition dictionary
    - `configuration` (Dict[str, Any]) - Module configuration dictionary
    - `assistantId` (str) - Associated assistant/space ID
    - `weight` (int) - Module weight/priority
    - `isExternal` (bool) - Whether module is external
    - `isCustomInstructionEnabled` (bool) - Whether custom instructions are enabled
    - `moduleTemplateId` (str | None) - Module template ID
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)

    **Used in:** `Space.modules`

#### Space.ScopeRule {#spacescoperule}

??? note "The `Space.ScopeRule` object represents a scope rule for a space"

    **Fields:**

    - `id` (str) - Unique scope rule identifier
    - `assistantId` (str) - Associated assistant/space ID
    - `title` (str) - Scope rule title
    - `companyId` (str) - Company ID
    - `rule` (Dict[str, Any]) - UniqueQL rule definition
    - `isAdvanced` (bool) - Whether rule uses advanced syntax
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)

    **Used in:** `Space.scopeRules`

#### Space.AssistantAccess {#spaceassistantaccess}

??? note "The `Space.AssistantAccess` object represents access control for a space"

    **Fields:**

    - `id` (str) - Unique access control identifier
    - `entityId` (str) - User or group ID
    - `entityType` (str) - Entity type (e.g., "USER", "GROUP")
    - `type` (str) - Access type (e.g., "READ", "WRITE")

    **Used in:** `Space.assistantAccess`

#### DeleteChatResponse {#deletechatresponse}

??? note "The `DeleteChatResponse` object contains the deleted chat ID"

    **Fields:**

    - `chat_id` (str) - ID of the deleted chat

    **Returned by:** `Space.delete_chat()`

## Related Resources

- [Message API](message.md) - Direct message management
- [Chat in Space Utility](../utilities/chat_in_space.md) - Helper functions
- [UniqueQL](../uniqueql.md) - Scope rule filtering

