---
name: unique-cli
description: Use the Unique SDK CLI in Claude Cowork to browse, search, upload, download, and manage Unique knowledge-base files.
allowed-tools: Bash
---

# Unique CLI

Use the `unique-cli` command for Unique knowledge-base operations inside Claude Cowork.

Authentication is automatic: the plugin prompts for Unique API configuration
when it is enabled, and a SessionStart hook writes those values to a private
config file whose path is exposed as `UNIQUE_CONFIG_PATH`. Never read or print
that config file. If `unique-cli` reports missing configuration, ask the user
to configure the plugin via `/plugin` (select unique-cli, then "Configure
options") and start a new session — do not try to work around it. If the API
responds with Unauthorized, ask the user to verify the configured
`UNIQUE_API_BASE` matches their key/app/user/company.

Examples:

```bash
unique-cli --help
unique-cli ls /
unique-cli search "quarterly report" --limit 10
unique-cli upload ./report.pdf /Reports
```

