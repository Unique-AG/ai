# Claude Cowork Unique CLI Plugin

This plugin bundles `unique-cli` for Claude Cowork and Claude Code. Cowork runs commands inside a Linux VM, while local Claude Code usage may run on macOS, so the plugin can ship binaries for both platforms:

- `bin/unique-cli-linux-amd64`
- `bin/unique-cli-linux-arm64`
- `bin/unique-cli-darwin-amd64`
- `bin/unique-cli-darwin-arm64`

`bin/unique-cli` dispatches to the right binary at runtime.

## Authentication

The plugin prompts for the Unique API configuration (`UNIQUE_API_KEY`, `UNIQUE_APP_ID`, `UNIQUE_USER_ID`, `UNIQUE_COMPANY_ID`, and optional `UNIQUE_API_BASE`) when it is enabled. Claude Code only injects those `userConfig` values into plugin subprocesses (hooks, MCP servers) — not into Bash tool commands. The plugin bridges that gap:

1. A `SessionStart` hook (`hooks/hooks.json` → `scripts/session-start.sh`) runs at session start with the `CLAUDE_PLUGIN_OPTION_*` variables available.
2. The hook calls `unique-cli write-config` to persist the values into `${CLAUDE_PLUGIN_DATA}/config.json` with mode `0600`. The data directory survives plugin updates.
3. The hook appends `export UNIQUE_CONFIG_PATH=...` (the path only, no secrets) to `$CLAUDE_ENV_FILE`, making the variable part of the session environment for all Bash tool calls.
4. `unique-cli` reads `UNIQUE_CONFIG_PATH` and uses the file values as fallbacks for any unset `UNIQUE_*` environment variables.

If configuration is missing or the API responds with Unauthorized, configure the plugin via `/plugin` → unique-cli → "Configure options". Verify that `UNIQUE_API_BASE` matches the gateway for the configured key/app/user/company, then start a new session (or run `/reload-plugins`).

Note the honest limitation: the config file is readable by any command running as the same OS user, including session Bash commands. Use a least-privilege, revocable API key, and restrict network egress where possible.

## Build

From the repository root:

```bash
./unique_sdk/claude-marketplace/plugins/unique-cli/build/build-plugin.sh
```

The script uses Docker and PyInstaller to build both Linux binaries. On macOS, it also builds the matching local macOS binary. Build artifacts are written outside the plugin directory (plugin installs copy the entire plugin folder, so artifacts inside it would bloat every install):

```text
unique_sdk/claude-marketplace/artifacts/dist/                                  # intermediate build output
unique_sdk/claude-marketplace/artifacts/bundles/unique-cli-plugin-<version>.zip
```

Upload the generated zip from `unique_sdk/claude-marketplace/artifacts/bundles/` to Claude Desktop/Cowork as the plugin package.

To build a specific set of targets, pass them explicitly:

```bash
./unique_sdk/claude-marketplace/plugins/unique-cli/build/build-plugin.sh linux/amd64 linux/arm64 darwin/arm64
```
