---
name: unique-cli-agentic-table
description: >-
  Read and drive Agentic Table (magic table / due-diligence) sheets through the
  unique-cli agentic-table command. Use when the user or task involves an
  Agentic Table: inspecting a sheet's state, a cell's value or lock state, a
  cell's edit history or its export artifacts; or running the full loop —
  creating a sheet, importing a questionnaire and sources, waiting for the
  agent to answer, and exporting the result. Access is enforced per sheet by
  the platform and varies from sheet to sheet; a denial is reported as
  `agentic-table: permission denied`.
---

# Unique CLI -- Agentic Table

Work with Agentic Table (a.k.a. magic table) sheets over the public magic-table
API. Every command is scoped to the current user/company automatically; you
never pass credentials.

Commands fall into two groups:

- **Read (Tier 0)** — `get-sheet`, `get-cell`, `cell-history`, `list-exports`.
  Never modify anything, never need confirmation.
- **Write** — `create-sheet`, `import`, `export`. These create a sheet, add
  questions and sources, start the agent run, and produce export artifacts.

## Permissions

Access is enforced **server-side, per sheet**. This is the part most likely to
trip you up, because it is not uniform: the same user can own one sheet, hold
edit access on a second, and read-only access on a third. Do not assume that
succeeding on one sheet means you can do the same thing on another.

There is no command yet that reports your access level on a sheet, so:

1. Start with a read (`get-sheet`) before attempting a write on a sheet you
   have not touched in this session. It costs one call and tells you whether
   the sheet is reachable at all.
2. Treat `agentic-table: permission denied` as **information, not failure**.
   It means the current user lacks the level that operation needs. Report it
   and ask the user how to proceed.
3. Never retry a denial with different ids to discover what you can reach.
   That is access probing, and it will not find anything you are entitled to.

Some rows are protected. A row whose review status is locked or final rejects
edits from everyone, including you — that is deliberate, and it usually means
a person has already approved that answer. Do not try to route around it.

## Read commands

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

## Write commands

### Create a sheet

```bash
unique-cli agentic-table create-sheet <assistant_id> [--name <name>] [--due-at <iso8601>]
```

Creates an empty sheet in a space. The printed `ID` is the `table_id` every
other command takes. Requires write access to the space.

```bash
unique-cli agentic-table create-sheet asst_123 --name "Vendor DDQ"
```

### Import questions and sources

```bash
unique-cli agentic-table import <table_id> [--question-file-id <id>]... [--question-text <text>]...
                                           [--source-file-id <id>]... [--context <text>]
                                           [--wait] [--timeout <seconds>]
```

Adds questions and/or source files. **Adding new questions starts the agent
run; adding only sources does not.** Ids and texts already on the sheet are
skipped. The call is rejected while the sheet is already processing.

`--wait` blocks until the triggered run finishes (default timeout 600s) so you
can chain an export. If only sources were added and no run started, that is
reported as a note rather than an error.

```bash
unique-cli agentic-table import mt_abc123 --question-file-id c_q --source-file-id c_src --wait
```

### Export answers

```bash
unique-cli agentic-table export <table_id> --type <TYPE>... [--wait] [--timeout <seconds>]
```

Generates `FULL_REPORT`, `QUESTIONS` or `AGENTIC_REPORT` artifacts. Generation
is asynchronous; `--wait` polls until each requested type is `DONE` and prints
the `contentId` to download. An artifact entering `ERROR` fails fast.

```bash
unique-cli agentic-table export mt_abc123 --type FULL_REPORT --wait
```

## Full loop

Create a sheet, populate and run it, then read the answers. Every step exits
non-zero on failure — including a rejection the backend reports in the response
body rather than as an HTTP error — so the steps chain safely with `&&`:

```bash
SHEET=$(unique-cli agentic-table create-sheet asst_123 --name "Vendor DDQ" --json | jq -r .sheetId) && \
unique-cli agentic-table import "$SHEET" --question-file-id c_questions --source-file-id c_sources --wait && \
unique-cli agentic-table export "$SHEET" --type FULL_REPORT --wait && \
unique-cli agentic-table get-sheet "$SHEET" --cells
```

To fill in an existing questionnaire from a sheet someone else has already
answered, skip the create and import steps: read the answers with
`get-sheet --cells` or `get-cell`, and use `cell-history` if you need to know
whether an answer came from a person or the assistant.

## Rules

1. `--row` and `--col` are **0-based** orders. Row 0 is the header row.
2. Fetch what you need, not everything. `get-cell` for one value,
   `get-sheet --cells` for an overview — don't dump a whole sheet unless asked.
3. Use `--wait` when a later step depends on the result, and only then. Without
   it, `import` and `export` return as soon as the request is accepted, and the
   answers or artifacts will not be ready yet.
4. Never re-run `import` with the same questions to "retry" — ids and texts
   already on the sheet are skipped, and a run that is already in flight will
   reject the call.
5. Tell the user what you changed. A sheet is shared, and someone else may be
   working in it.
6. Use `--json` when you need to parse fields programmatically (e.g. reading a
   `contentId` before downloading an export); use the default formatted output
   when summarising for a person.

## Prerequisites

The platform sets these environment variables automatically:

```bash
UNIQUE_USER_ID
UNIQUE_COMPANY_ID
UNIQUE_API_KEY
UNIQUE_APP_ID
```

Install: `pip install unique-sdk`
