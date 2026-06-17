---
name: unique-cli
description: Use the Unique SDK CLI in Claude Cowork to browse, search, upload, download, and manage Unique knowledge-base files.
allowed-tools: Bash
---

# Unique CLI

Use the `unique-cli` command for Unique knowledge-base operations inside Claude Cowork.

Required environment variables:

```bash
export UNIQUE_API_KEY="ukey_..."
export UNIQUE_APP_ID="app_..."
export UNIQUE_USER_ID="user_..."
export UNIQUE_COMPANY_ID="company_..."
```

Examples:

```bash
unique-cli --help
unique-cli ls /
unique-cli search "quarterly report" --limit 10
unique-cli upload ./report.pdf /Reports
```

