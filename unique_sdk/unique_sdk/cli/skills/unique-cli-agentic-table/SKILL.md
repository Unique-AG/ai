---
name: unique-cli-agentic-table
description: >-
  Read Agentic Table (magic table / due-diligence) sheets through the
  unique-cli agentic-table command. Use when the user or task involves
  inspecting an Agentic Table: a sheet's state and metadata, a specific
  cell's value or lock state, a cell's edit/answer history, or the sheet's
  generated export artifacts (reports, question exports). These are
  read-only (Tier 0) commands — they never modify the sheet and never
  require confirmation. Access to each sheet is enforced by the platform;
  a denial is reported as `agentic-table: permission denied`.
---

# Unique CLI -- Agentic Table (read)

Inspect Agentic Table (a.k.a. magic table) sheets over the public magic-table
API. Every command is scoped to the current user/company automatically; you
never pass credentials. Sheet-role access (Owner / Can manage / Can edit) is
enforced **server-side** — if you are not entitled to a sheet the command exits
with `agentic-table: permission denied` rather than returning data.

All commands here are **reads only**. There are no write commands in this skill.

## Commands

### Sheet summary

```bash
unique-cli agentic-table get-sheet <table_id>
```

Shows the sheet name, state, and row count. Add flags for more detail:

| Flag | Effect |
|------|--------|
| `--metadata` | Include sheet-level metadata entries |
| `--cells` | Include cell values (row, column, text snippet) |
| `--json` | Print the raw sheet JSON instead of the formatted view |

```bash
unique-cli agentic-table get-sheet mt_abc123 --metadata --cells
```

### Single cell

```bash
unique-cli agentic-table get-cell <table_id> --row N --col N
```

Shows one cell's text and lock state. `--row`/`--col` are 0-based orders.
Add `--json` for the raw cell record.

```bash
unique-cli agentic-table get-cell mt_abc123 --row 1 --col 2
```

### Cell history

```bash
unique-cli agentic-table cell-history <table_id> --row N --col N
```

Shows a single cell's log/edit history (actor, timestamp, source message id,
and the logged text) newest-to-oldest as returned by the API. Add `--json`
to get the raw log entries.

```bash
unique-cli agentic-table cell-history mt_abc123 --row 1 --col 2
```

### Export artifacts

```bash
unique-cli agentic-table list-exports <table_id>
```

Lists the sheet's generated exports (full report, question export, agentic
report) with their state. The content id needed to download a file is only
present once an artifact reaches the `DONE` state. Add `--json` for the raw
list.

```bash
unique-cli agentic-table list-exports mt_abc123
```

## Rules

1. Treat these as read-only diagnostics. To answer a question about a sheet,
   fetch exactly what you need (`get-cell` for one value, `get-sheet --cells`
   for an overview) rather than dumping the whole sheet unless asked.
2. `--row` and `--col` are **0-based** orders. Row 0 is the header row.
3. A `agentic-table: permission denied` line means the current user cannot
   access that sheet. Do not retry with different ids to probe access — report
   the denial and stop.
4. Use `--json` when you need to parse fields programmatically (e.g. to read a
   `contentId` before downloading an export); use the default formatted output
   when summarising for the user.

## Prerequisites

The platform sets these environment variables automatically:

```bash
UNIQUE_USER_ID
UNIQUE_COMPANY_ID
UNIQUE_API_KEY
UNIQUE_APP_ID
```

Install: `pip install unique-sdk`
