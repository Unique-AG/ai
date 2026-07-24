# Account Review console — v005

Multi-file HTML sources, combined into **one** platform file. **All business
data is live from MCP** — there is no agent “rebuild HTML” step.

## Layout

```
dashboard-v005/
  build.py                 # combine pages + inline CSS
  src/
    config.json            # ← MCP server id & other build variables
    config.example.json    # template for new environments
    shell.html
    styles.css
    pages/
      manifest.json
      clients.html
      main.html
  ../dashboard-v005.html   # PLATFORM ARTIFACT
```

## Configuration

Edit `src/config.json`:

| Key | Placeholder | Purpose |
| --- | --- | --- |
| `mcp_server` | `__MCP_SERVER__` | Unique MCP connector id |
| `rm_name` | `__RM_NAME__` | Greeting name |
| `page_title` | `__PAGE_TITLE__` | HTML `<title>` |
| `poll_ms` | `__POLL_MS__` | `data-unique-source-poll` interval |
| `connectors_online` | `__CONNECTORS_ONLINE__` | Footer label |

Overrides (later wins):

1. `src/config.json`
2. Env: `DASHBOARD_MCP_SERVER`, `DASHBOARD_RM_NAME`, `DASHBOARD_PAGE_TITLE`,
   `DASHBOARD_POLL_MS`, `DASHBOARD_CONNECTORS_ONLINE`
3. CLI flags

## Build

```bash
python build.py
python build.py --mcp-server mcp_thvxcf56tka96a8lmv2ilwfd
python build.py --print-config
DASHBOARD_MCP_SERVER=mcp_xxx python build.py
```

→ `../dashboard-v005.html`

## Live bindings

| UI | MCP tool | List id |
| --- | --- | --- |
| Client detail pages | `list_rows` (clients) | `clientPages` |
| Attention rail | `list_rows` (Needs Remediation) | `attentionLive` |
| KPI tiles | `count_by` (status) | `statusKpis` |
| Portfolio table | `list_rows` (clients) | `clientsLive` |

### Placeholder interpolation

Inside a list row, `{field}` is only filled when the host sets an attribute via
`data-unique-attr-*`. Use:

- `data-unique-attr-href` / `data-unique-attr-id` for links and anchors
- `data-unique-attr-data-unique-source-args` for `callTool` args
- `data-unique-attr-data-unique-payload` for `sendPrompt` payloads

A plain `data-unique-payload='…{client_name}…'` stays literal in chat.
