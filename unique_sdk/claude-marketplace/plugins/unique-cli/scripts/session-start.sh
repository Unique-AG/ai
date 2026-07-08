#!/usr/bin/env bash
set -euo pipefail

# SessionStart bridge for plugin userConfig values.
#
# Claude Code exports userConfig values as CLAUDE_PLUGIN_OPTION_* only to
# plugin subprocesses (hooks, MCP/LSP servers, monitors) — NOT to Bash tool
# commands run during the session. This hook persists the values into a
# 0600 config file in the persistent plugin data directory and publishes
# only the file path to the session environment, so `unique-cli` invoked
# from the Bash tool can pick the values up via UNIQUE_CONFIG_PATH.

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] || [ -z "${CLAUDE_PLUGIN_DATA:-}" ]; then
  exit 0
fi

mkdir -p "$CLAUDE_PLUGIN_DATA"
config_file="$CLAUDE_PLUGIN_DATA/config.json"

# The bin/unique-cli wrapper maps CLAUDE_PLUGIN_OPTION_* to UNIQUE_* before
# exec'ing the real binary, so write-config sees the plugin configuration.
umask 077
"$CLAUDE_PLUGIN_ROOT/bin/unique-cli" write-config --out "$config_file"
export UNIQUE_CONFIG_PATH="$config_file"

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  printf 'export UNIQUE_CONFIG_PATH="%s"\n' "$config_file" >> "$CLAUDE_ENV_FILE"
fi
