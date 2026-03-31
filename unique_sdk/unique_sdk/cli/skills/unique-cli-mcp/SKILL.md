---
name: unique-cli-mcp
description: >-
  Call MCP (Model Context Protocol) server tools on the Unique AI Platform
  using the unique-cli mcp command. Use when the user asks to invoke,
  call, or execute an MCP tool, or when they need to send a JSON payload
  to an MCP server through the CLI. The JSON payload is forwarded 1:1
  to the platform's MCP call-tool API.
---

# Unique CLI -- MCP Tool Calls

Call MCP server tools registered on the Unique AI Platform directly from the command line. The JSON payload containing the tool name and arguments is forwarded 1:1 to the platform API.

## JSON Payload Schema

The payload is a JSON object with two fields:

```json
{
  "name": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": 42,
    "nested": {"key": "value"}
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | The MCP tool name to invoke |
| `arguments` | No | Object of key-value arguments (defaults to `{}`) |

## Basic Usage

```bash
# Call an MCP tool with inline JSON
unique-cli mcp -c <chat_id> -m <message_id> \
  '{"name": "search_documents", "arguments": {"query": "quarterly report"}}'

# Short form
unique-cli mcp -c chat_abc123 -m msg_def456 \
  '{"name": "get_weather", "arguments": {"city": "Zurich"}}'
```

## Input Sources

The JSON payload can come from three sources (exactly one required):

### Inline JSON (positional argument)

```bash
unique-cli mcp -c chat_123 -m msg_456 '{"name": "tool", "arguments": {"key": "value"}}'
```

### From a file

```bash
unique-cli mcp -c chat_123 -m msg_456 --file payload.json
```

### From stdin (pipe)

```bash
cat payload.json | unique-cli mcp -c chat_123 -m msg_456 --stdin

echo '{"name": "tool", "arguments": {}}' | unique-cli mcp -c chat_123 -m msg_456 --stdin
```

## Command Reference

```
unique-cli mcp [--chat-id <id>] [--message-id <id>] [PAYLOAD | --file <path> | --stdin]
```

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--chat-id` | `-c` | Yes | Chat ID for the conversation context |
| `--message-id` | `-m` | Yes | Message ID for the conversation context |
| `PAYLOAD` | | One of three | Inline JSON string |
| `--file` | `-f` | One of three | Path to a JSON file |
| `--stdin` | | One of three | Read JSON from stdin |

## Output Format

```
MCP tool call: search_documents
Server: mcp_srv_abc123

[text] Search completed successfully. Found 3 results.
[text] 1. Annual Report 2025 — Revenue grew 15% year-over-year...
```

Each content item is prefixed with its type: `[text]`, `[image]`, `[audio]`, `[resource_link]`, or `[resource]`.

Error responses show `(ERROR)` in the header:

```
MCP tool call: search_documents (ERROR)
Server: mcp_srv_abc123

[text] Tool execution failed: invalid argument "limti"
```

## Scripting Examples

### Call a tool and capture output

```bash
result=$(unique-cli mcp -c chat_123 -m msg_456 \
  '{"name": "summarize", "arguments": {"document_id": "doc_789"}}')
echo "$result"
```

### Build payload dynamically

```bash
payload=$(jq -n \
  --arg name "search_documents" \
  --arg query "$SEARCH_QUERY" \
  '{"name": $name, "arguments": {"query": $query}}')

unique-cli mcp -c chat_123 -m msg_456 "$payload"
```

### Pipe from a generated payload

```bash
python generate_payload.py | unique-cli mcp -c chat_123 -m msg_456 --stdin
```

## Prerequisites

Requires these environment variables:

```bash
UNIQUE_API_KEY    # API key (ukey_...)
UNIQUE_APP_ID     # App ID (app_...)
UNIQUE_USER_ID    # User ID
UNIQUE_COMPANY_ID # Company ID
```

Install: `pip install unique-sdk`
