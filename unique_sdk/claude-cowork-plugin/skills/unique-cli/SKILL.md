---
name: unique-cli
description: Use the Unique SDK CLI in Claude Cowork to browse, search, upload, download, and manage Unique knowledge-base files.
allowed-tools: Bash
---

# Unique CLI

Use the `unique-cli` command for Unique knowledge-base operations inside Claude Cowork.

The plugin option `skillFolder` can point to either a Unique folder name or a
scope ID containing Claude skills in the Unique knowledge base. When skills are
needed, read them from that folder with the existing file commands:

```bash
unique-cli ls "$UNIQUE_SKILL_FOLDER"
unique-cli search "SKILL.md" --folder "$UNIQUE_SKILL_FOLDER"
unique-cli read cont_abc123
```

Examples:

```bash
unique-cli --help
unique-cli ls /
unique-cli search "quarterly report" --limit 10
unique-cli upload ./report.pdf /Reports
```

