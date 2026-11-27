# MCP API

The MCP API lets an assistant call tools exposed by connected MCP servers.

Use `unique_sdk.MCP` when you want to trigger one tool call from an assistant context and get normalized tool output content back.

## Methods

??? example "`unique_sdk.MCP.call_tool` - Call an MCP tool"

    Call one MCP tool with arguments and message context.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `name` (str, required) - Tool name exposed by MCP
    - `messageId` (str, required) - Message ID associated with the tool call
    - `chatId` (str, required) - Chat ID associated with the tool call
    - `arguments` (dict[str, Any], required) - Tool arguments payload

    **Returns:**

    Returns an [`MCP`](#mcp) object that includes tool output content.

    **Example:**

    ```python
    result = unique_sdk.MCP.call_tool(
        user_id=user_id,
        company_id=company_id,
        name="search_documents",
        messageId=message_id,
        chatId=chat_id,
        arguments={"query": "Q4 revenue"},
    )

    for item in result["content"]:
        print(item["type"])
    ```

!!! tip "Async variant"
    Use `unique_sdk.MCP.call_tool_async(...)` for async workflows.

??? example "`unique_sdk.MCP.list_servers` - List MCP servers that can be attached to a space"

    List the company's MCP servers (connectors) with the tools the company has enabled. Use the ids and tool names in the `mcpServers` field of `Space.create_space` and `Space.update_space`. Never returns server URLs or credentials.

    Requires a role that may configure spaces.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier

    **Returns:**

    Returns a [`McpServersResponse`](#mcpserversresponse) object.

    **Example:**

    ```python
    servers = unique_sdk.MCP.list_servers(user_id=user_id, company_id=company_id)

    for server in servers["mcpServers"]:
        print(server["id"], server["name"], [tool["name"] for tool in server["tools"]])
    ```

!!! tip "Async variant"
    Use `unique_sdk.MCP.list_servers_async(...)` for async workflows.

## Input Types

#### CallToolParams {#calltoolparams}

??? note "The `CallToolParams` type defines parameters for MCP tool calls"

    **Fields:**

    - `name` (str, required) - Tool name to invoke
    - `messageId` (str, required) - Source message ID
    - `chatId` (str, required) - Source chat ID
    - `arguments` (dict[str, Any], required) - Tool arguments

    **Used in:** `MCP.call_tool()`

## Return Types

#### MCP {#mcp}

??? note "The `MCP` object represents one tool call result"

    **Fields:**

    - `content` (list[[`CallToolContentDto`](#calltoolcontentdto)]) - Tool output content items
    - `isError` (bool | None) - Optional error marker from server
    - `mcpServerId` (str | None) - Optional MCP server ID
    - `name` (str | None) - Optional tool name echoed by server

    **Returned by:** `MCP.call_tool()`, `MCP.call_tool_async()`

#### McpServersResponse {#mcpserversresponse}

??? note "The `McpServersResponse` object lists the company's MCP servers"

    **Fields:**

    - `mcpServers` (list[McpServerDto]) - Servers sorted by name:
        - `id` (str) - MCP server ID
        - `name` (str) - MCP server name
        - `description` (str | None) - MCP server description
        - `requiresOAuth` (bool) - Whether each user has to sign in before the server's tools run
        - `isSpaceRestricted` (bool) - Whether the server may only be attached to the spaces in `allowedSpaceIds`
        - `allowedSpaceIds` (list[str]) - Space IDs the server may be attached to. Empty when unrestricted.
        - `tools` (list[McpServerToolDto]) - Tools the company has enabled, each with `name` (str) and `description` (str | None)

    **Returned by:** `MCP.list_servers()`, `MCP.list_servers_async()`

#### CallToolContentDto {#calltoolcontentdto}

??? note "A single content item in MCP tool output"

    **Fields:**

    - `type` (Literal["text", "image", "audio", "resource_link", "resource"]) - Content kind
    - `text` (str | None, optional) - Text payload for `type="text"`
    - `data` (str | None, optional) - Base64 payload for `type="image"` or `type="audio"`
    - `mimeType` (str | None, optional) - MIME type for binary/link content
    - `uri` (str | None, optional) - URI for `type="resource_link"`
    - `name` (str | None, optional) - Display name for `type="resource_link"`
    - `description` (str | None, optional) - Description for `type="resource_link"`
    - `resource` ([`CallToolTextResourceDto`](#calltooltextresourcedto) | [`CallToolBlobResourceDto`](#calltoolblobresourcedto) | None, optional) - Inline resource payload for `type="resource"`

#### CallToolTextResourceDto {#calltooltextresourcedto}

??? note "Text resource payload"

    **Fields:**

    - `uri` (str) - Resource URI
    - `mimeType` (str | None) - Resource MIME type
    - `text` (str) - Resource text content

#### CallToolBlobResourceDto {#calltoolblobresourcedto}

??? note "Blob resource payload"

    **Fields:**

    - `uri` (str) - Resource URI
    - `mimeType` (str | None) - Resource MIME type
    - `blob` (str) - Base64-encoded blob payload
