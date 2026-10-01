# Custom module with MCP tools

An external module that calls the MCP tools configured on its space.

The module does not discover MCP servers on its own. The space decides which
servers it may use, and the platform hands the connected ones to the module on
every message.

## 1. Configure the module

Store this on the module's configuration, replacing the placeholders
(`module_configuration.example.json`):

```json
{
  "languageModel": "AZURE_GPT_4o_2024_1120",
  "tools": [
    {
      "name": "jira_search",
      "isEnabled": true,
      "configuration": {
        "mcpTool": true,
        "mcpServerId": "<atlassian-mcp-server-id>"
      }
    },
    {
      "name": "search_repositories",
      "isEnabled": true,
      "configuration": {
        "mcpTool": true,
        "mcpServerId": "<github-mcp-server-id>"
      }
    }
  ]
}
```

Two fields do the work. `mcpTool: true` marks the entry as an MCP tool, and
`mcpServerId` is the id of the MCP server row — not its display name. `name` is
the tool's name on that server. A name that no enabled tool matches is skipped,
and that server never reaches the space.

Add further tools for the same server as more entries carrying the same
`mcpServerId`. Keep the object flat: when it also has `space` and `agent` keys,
the platform reads `space.tools` instead of `tools`.

`languageModel` is the model this module answers with. Use a model registered
for your company.

`configuration.py` builds the same JSON from Pydantic models, if you generate
your configuration in code:

```bash
uv run python -m mcp_custom_module.configuration
```

Dump it with `model_dump(by_alias=True)` so the keys stay camelCase. Do not use
`ToolBuildConfig` for these entries — it has no `mcpTool` or `mcpServerId`
field and drops both.

## 2. Connecting is the platform's job

Saving the space turns the tool entries above into the space's MCP server
assignments. From then on the chat itself asks each server whether the current
user is authenticated, and shows a **Connect** banner above the message box for
any server that is not. **Reconnect** appears when a session expires mid-chat.

This module renders none of that. It only sees the result: servers the user has
connected arrive on the event, and the rest do not.

## 3. Run the app

```bash
cd unique_sdk/examples/mcp-custom-module
cp unique.env.example unique.env   # then fill it in
uv run python -m mcp_custom_module.app
```

The app listens on port 5001 and serves the webhook at `/webhook`. Point the
module's webhook at it; use a tunnel such as ngrok when developing locally.
Signature verification is handled by `build_unique_custom_app`.

## 4. Use it

Send any message in the space. The module replies with its configured model
and the tools currently connected for you:

```
Model `AZURE_GPT_4o_2024_1120`. Connected MCP tools:

- **Atlassian**
    - `atlassian_jira_search` — Search Jira issues using JQL
- **GitHub**
    - `github_search_repositories` — Search for GitHub repositories
```

To call a tool, send its name and arguments as JSON:

```json
{ "name": "atlassian_jira_search", "arguments": { "jql": "project = UN" } }
```

Note the names. The event carries the namespaced `<server>_<tool>` form, which
is what `MCP.call_tool` expects. The bare names in the stored configuration
(`jira_search`) will not route.

If nothing is connected, the module says so and stops, rather than failing a
tool call.

## How the handler works

`app.py` is a single `handle_event(event: ChatEvent) -> int` passed to
`build_unique_custom_app`:

- `event.payload.mcp_servers` — servers connected for this user, each with its
  tools. Empty means the user has not connected anything yet.
- `event.payload.configuration` — the module configuration from step 1, which
  is where `languageModel` is read from.
- `unique_sdk.MCP.call_tool(...)` — runs a tool, addressed by its namespaced
  name, scoped to this chat and assistant message.
- `ChatService` — writes the reply onto the assistant message the platform
  already created for this turn.
