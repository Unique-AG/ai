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
| `--message-id` | `-m` | No | Message ID for the conversation context. Optional — resolved from `$UNIQUE_TURN_IDENTITY_FILE` (preferred) or `$UNIQUE_MESSAGE_ID` when omitted. |
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

## Citation Rules

Cite every fact from an MCP tool with the `[mcpsourceN]` marker that the command printed in the `Sources` footer beneath the tool output, placed right after the fact. The Unique platform turns each marker in your final answer into a `<sup>N</sup>` footnote and a reference chip. Without a marker, an MCP fact shows as plain text and the answer counts as ungrounded.

```
ACME's Q3 revenue was 1.2M [mcpsource1], up from 0.9M a year earlier [mcpsource2].
```

**Rules** (enforced by the platform's reference post-processor, which reads `.unique/mcp-refs.jsonl` rather than your prose):

1. **Numbers are chat-wide.** They never restart at 1, so a high first number in a turn is normal. A number from an earlier turn still resolves to the same source, and re-fetching an item returns its old number. NEVER re-run a tool only to refresh or verify numbers. If compaction dropped a footer you need, answer from the sources still visible; re-fetch one at most once per turn, and only for its content.
2. **Format.** Write `mcpsource` singular with a digit number: `[mcpsource1]`, never `[McpSource 1]`, `[mcpsource one]` or `[mcpsources 1, 2]`. `[mcpsourceN]` is for MCP results only: knowledge-base results use `[sourceN]`, web results `[websourceN]`; never mix them. Prefer the one most relevant source per fact. Never invent a number for a remembered or inferred fact, and none for a result without a `Sources` footer.
3. **Enrich the marker with the item's title and URL**, separated by semicolons:
   `[mcpsource2;ABC-123 — Fix login flow;https://acme.atlassian.net/browse/ABC-123]`.
   The chip is then labelled with the title and links to the item.
   - `N` is the footer number of the result the item came from. Never carry a number from one result over to an item from another.
   - Cite one marker per item, meaning each entity whose value you report. A footer may list one number per item, or one number for a whole result set (a search returning many matches as one blob). In that case reuse the same `N` for each item, each with its own title and URL: chips are keyed on source, title and URL, so they render separately. Never fall back to plain `[mcpsourceN]` just to avoid repeating a number.
   - **Title**: the item's own short name from the result (issue key + summary, page title, email subject, channel + date). No `;` or brackets, under ~120 characters. Without a per-item name, name the call (`get_chart GOOGL`).
   - **URL**: copy it from the output, or build it only from values in the output (`<base>/browse/<KEY>`). The platform checks the host against the output and drops anything else. Prefer the user-facing permalink over API URLs (`.../rest/api/...`). Reading an attachment or file a result pointed at still cites that result's permalink.
   - If the output has a link for the item (`Permalink:`, `url`, `webUrl`, `https://…`), even inside a multi-item blob, you MUST include it. `[mcpsourceN;URL]` is always fine; `[mcpsourceN;title]` only when the result has no link for the item; plain `[mcpsourceN]` only when it has neither.
4. **Action tools too.** When you report what a create, update or delete tool created or changed (a ticket key, page link or ID), cite it with the marker from that result's `Sources` footer. An action whose outcome you do not mention needs no citation.

## Prerequisites

Requires these environment variables:

```bash
UNIQUE_USER_ID    # User ID (required)
UNIQUE_COMPANY_ID # Company ID (required)
UNIQUE_API_KEY    # API key — optional on localhost / secured cluster
UNIQUE_APP_ID     # App ID — optional on localhost / secured cluster
```

Install: `pip install unique-sdk`
