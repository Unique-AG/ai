# MCP Space Chat — call Unique spaces as sub-agents with a live chat window

An MCP server that lets any MCP host (Claude, VS Code Copilot, Goose,
Postman, MCPJam, …) delegate work to **Unique spaces** (specialized
sub-agents) and shows the running conversation in a **live chat window**
rendered via [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview)
/ [MCP-UI](https://mcpui.dev/) — the same chrome-less chat embed
(`/chat/embed`) that the Unique browser extension uses, complete with native
streaming and auto-scrolling.

## How it works

```
MCP host (Claude, …)
 ├── model ── tools/call ──> mcp-space-chat (FastMCP)
 │                             ├── list_spaces        Space.get_spaces
 │                             ├── ask_space          Space.create_message  ──> Unique platform
 │                             └── get_space_answer   Space.get_latest_message (poll)
 └── sandboxed iframe (ui://space-chat/chat-window)
       └── nested iframe: {frontend}/chat/embed/{chatId}?spaceId=…
             └── GraphQL WebSocket streaming + auto-scroll (chat frontend)
```

1. The model calls `list_spaces` to discover the spaces (sub-agents) the
   logged-in user can access.
2. `ask_space(space_id, prompt)` creates a user message in the space via
   `unique_sdk.Space.create_message` and returns immediately with the
   `chatId`. The tool result carries:
   - `_meta.ui.resourceUri` → MCP Apps hosts render the
     `ui://space-chat/chat-window` HTML resource in a sandboxed iframe. The
     wrapper does the `ui/initialize` handshake, receives the tool result via
     `ui/notifications/tool-result`, and mounts a nested iframe with the real
     Unique chat embed (`structuredContent.embedUrl`).
   - a legacy MCP-UI `externalUrl` embedded resource → MCP-UI hosts iframe the
     embed URL directly.
3. The chat frontend inside the iframe streams the space's answer over its
   GraphQL WebSocket and auto-scrolls — nothing to re-implement.
4. The model calls `get_space_answer(chat_id)` to poll until the assistant
   stops streaming and pull the final answer text into its own context (it
   cannot read the iframe).
5. Follow-up questions typed by the *user* happen directly in the embedded
   chat input; follow-ups by the *model* go through `ask_space` with the same
   `chatId`.

## Tools

| Tool | Purpose |
|------|---------|
| `list_spaces(name?)` | List spaces (sub-agents) available to the current user. |
| `ask_space(space_id, prompt, chat_id?)` | Send a prompt to a space; returns `chatId` + renders the live chat window. |
| `get_space_answer(chat_id, max_wait?)` | Wait until the space finished answering and return the final text + references. |

## Platform prerequisites

The embedded chat window is the real Unique chat frontend loaded in an
iframe, so the target environment must allow that framing:

- **CSP `frame-ancestors`** — the chat app's Content Security Policy must
  allowlist the MCP host's iframe origin. This is the same mechanism already
  used for the browser extension (`CSP_FRAME_ANCESTORS_EXTENSION` /
  `CONTENT_SECURITY_POLICY_VALUE` in
  `next/apps/chat/deploy/<env>/values.yaml` in the monorepo). For Claude, the
  sandbox origin is host-controlled (e.g. `https://*.claudemcpcontent.com`);
  for other hosts consult their documentation. Without this the browser
  refuses to render the nested iframe.
- **Auth caveat** — `/chat/embed` authenticates via OIDC tokens in the
  browser's `localStorage`. Inside a third-party iframe, storage is
  partitioned, so an existing Unique session does not carry over
  automatically; the embed then shows its "Open Unique to sign in" state. The
  chat window offers an "Open in Unique" button as a fallback / deep link. A
  durable fix (e.g. a short-lived token handoff to the embed) is a monorepo
  change and out of scope for this tutorial.

## Setup

Requirements: Python ≥ 3.12, [uv](https://docs.astral.sh/uv/).

```bash
cd tutorials/mcp/mcp_space_chat
uv sync
```

Copy and fill the env examples:

```bash
cp unique.env.example unique.env        # Unique API credentials + frontend URL
cp unique_mcp.env.example unique_mcp.env  # server bind + public URL
cp zitadel.env.example zitadel.env      # Zitadel OIDC proxy
```

Key settings:

| Variable | Purpose |
|----------|---------|
| `UNIQUE_APP_KEY` / `UNIQUE_APP_ID` / `UNIQUE_API_BASE_URL` | Unique platform API credentials. |
| `UNIQUE_FRONTEND_BASE_URL` | **Required.** Unique web app origin for the chat embed, e.g. `https://next.qa.unique.app`. |
| `UNIQUE_AUTH_USER_ID` / `UNIQUE_AUTH_COMPANY_ID` | Fallback identity when there is no OAuth session (local dev only). |
| `UNIQUE_MCP_LOCAL_BASE_URL` | Local bind address (this tutorial defaults to `http://127.0.0.1:8004`). |
| `ZITADEL_*` | OIDC proxy settings (see `mcp_search` tutorial for details). |

Run the server:

```bash
uv run mcp-space-chat
```

## Trying it out

- **MCPJam / MCP inspector (legacy MCP-UI path):** connect to
  `http://127.0.0.1:8004/mcp`, call `ask_space`, and the embedded
  `externalUrl` resource renders the chat iframe directly.
- **Claude (MCP Apps path):** expose the server publicly (e.g. ngrok), add it
  as a connector, and ask Claude to e.g. "list my Unique spaces, then ask the
  Research space to summarize X". The chat window renders inline while the
  space answers.

## Identity

Per-request identity follows the same rules as the `mcp_search` tutorial:
trusted `_meta` (`user_id`/`company_id`) from Unique AI, then Zitadel JWT
claims, then Zitadel `/userinfo`, and `UNIQUE_AUTH_*` env only when no OAuth
session is present (see `unique_mcp.get_unique_settings_async`).

## Deploy to Azure

Two paths — both ship with this package:

| Path | Entry | Best for |
|------|-------|----------|
| Azure App Service | [`./deploy.sh`](deploy.sh) | Quick demos / Claude connectors |
| ACI + Caddy + Key Vault | [`terraform/`](terraform/) | Custom domain + HTTPS + secrets |

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full walkthrough. Short version (App Service):

```bash
az group create --name rg-lab-demo-001-unique-space-chat-mcp --location swedencentral
export UNIQUE_FRONTEND_BASE_URL=https://next.qa.unique.app
./deploy.sh
# then set UNIQUE_APP_* / ZITADEL_* secrets and register the OAuth callback in Zitadel
```

MCP endpoint after deploy: `https://unique-space-chat-mcp.azurewebsites.net/mcp`

## Tests

```bash
uv run pytest
```
