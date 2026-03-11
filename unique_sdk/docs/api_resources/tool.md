# Tool API

The Tool API allows you to persist and retrieve tool call invocations associated with chat messages.

## Overview

The Tool resource provides methods to:

- Batch-create tool invocations (call + optional response) for a message
- List tool invocations by message ID(s)
- Automatically paginate when querying more than 200 message IDs

Each tool invocation represents a full round-trip: the assistant requesting a function call and (optionally) the tool's response. Under the hood, the backend stores these as paired rows in a single `MessageTool` table, but the SDK always returns the merged view.

## Methods

??? example "`unique_sdk.Tool.create_many` - Batch-create tool invocations"

    Create one or more tool invocations for a message. Each item includes the function call details and an optional response.

    **Parameters:**

    - `messageId` (str, required) - Message ID to attach the tools to
    - `tools` (list[[`ToolItem`](#toolitem)], required) - List of tool invocations to create (max 50)

    **Returns:**

    Returns a [`ListObject`](#listobject) containing [`Tool`](#tool) objects.

    **Example:**

    ```python
    result = unique_sdk.Tool.create_many(
        user_id=user_id,
        company_id=company_id,
        messageId=message_id,
        tools=[
            {
                "externalToolCallId": "call_abc123",
                "functionName": "get_weather",
                "arguments": {"location": "Zurich"},
                "roundIndex": 0,
                "sequenceIndex": 0,
                "response": {"content": '{"temp": 18, "unit": "celsius"}'},
            },
            {
                "externalToolCallId": "call_def456",
                "functionName": "get_calendar",
                "arguments": {"date": "2026-03-10"},
                "roundIndex": 0,
                "sequenceIndex": 1,
            },
        ],
    )

    for tool in result["data"]:
        print(tool["functionName"], tool["response"])
    ```

??? example "`unique_sdk.Tool.list` - List tools by message IDs"

    Retrieve all tool invocations for one or more messages. Pass message IDs as a comma-separated string.

    Automatically paginates when more than 200 message IDs are provided — the SDK splits the IDs into chunks, issues one GET per chunk, and merges all results into a single `ListObject`. If the message IDs string is empty, returns an empty `ListObject` without calling the API.

    **Parameters:**

    - `messageIds` (str, required) - Comma-separated message IDs to query

    **Returns:**

    Returns a [`ListObject`](#listobject) containing [`Tool`](#tool) objects.

    **Example:**

    ```python
    tools = unique_sdk.Tool.list(
        user_id=user_id,
        company_id=company_id,
        messageIds=",".join(all_message_ids),
    )

    for tool in tools["data"]:
        print(tool["functionName"], tool["arguments"])
    ```

!!! tip "Async variants"
    All methods have async counterparts: `create_many_async` and `list_async`.

## Input Types

#### ToolItem {#toolitem}

??? note "The `ToolItem` type defines a tool invocation to create"

    **Fields:**

    - `externalToolCallId` (str, required) - External identifier for the tool call (matches the LLM's `tool_call.id`)
    - `functionName` (str, required) - Name of the function that was called
    - `arguments` (dict[str, Any] | None, optional) - Function arguments as a JSON-serializable dict
    - `roundIndex` (int, required) - Which round of tool use this belongs to (0-based)
    - `sequenceIndex` (int, required) - Order within a round for parallel calls (0-based)
    - `response` ([`ToolResponse`](#toolresponse) | None, optional) - The tool's response, if available

    **Used in:** `Tool.create_many()`

#### ToolResponse {#toolresponse}

??? note "The `ToolResponse` type defines the response from a tool invocation"

    **Fields:**

    - `content` (str | None, optional) - The tool's response content (typically JSON-serialized)

    **Used in:** `ToolItem.response`

## Return Types

#### Tool {#tool}

??? note "The `Tool` object represents a complete tool invocation (call + response)"

    **Fields:**

    - `id` (str) - Unique identifier for this tool invocation
    - `externalToolCallId` (str) - External identifier matching the LLM's `tool_call.id`
    - `functionName` (str) - Name of the function that was called
    - `arguments` (dict[str, Any] | None) - Function arguments
    - `roundIndex` (int) - Round of tool use (0-based)
    - `sequenceIndex` (int) - Sequence within a round (0-based)
    - `messageId` (str) - Message this tool invocation belongs to
    - `response` (dict[str, Any] | None) - The tool's response (contains `id`, `content`, `toolCallId`, `createdAt`)
    - `createdAt` (str) - Creation timestamp (ISO 8601)

    **Returned by:** `Tool.create_many()`, `Tool.list()`

#### ListObject {#listobject}

??? note "The `ListObject` type represents a paginated list of tools"

    **Fields:**

    - `data` (list[Tool]) - List of tool objects
    - `has_more` (bool) - Whether there are more items to retrieve
    - `object` (str) - Object type identifier (always "list")

    **Returned by:** `Tool.create_many()`, `Tool.list()`

## Related Resources

- [Message API](message.md) - Manage the messages that tool invocations are attached to
