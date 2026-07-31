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
- **Write (Tier 1)** — `create-sheet`, `import`, `export`, `rerun-row`. These
  create a sheet, add questions and sources, start the agent run, produce
  export artifacts, and redo a single answer. None of them prompts for
  confirmation, but they do change a shared artifact, so say what you did
  afterwards.

  The first three only add. `rerun-row` is the exception: it replaces the
  answer in the row you name. The previous answer stays in `cell-history` and
  a settled row is refused outright, so the change is recoverable and the
  approved rows are protected — but name the row you are redoing when you
  report back, and check you have the right one first.

## Permissions

Access is enforced **server-side, per sheet**. This is the part most likely to
trip you up, because it is not uniform: the same user can own one sheet, hold
edit access on a second, and read-only access on a third. Do not assume that
succeeding on one sheet means you can do the same thing on another.

There is no command yet that reports your access level on a sheet. Until there
is, you cannot establish up front what you are allowed to do — a successful
`get-sheet` proves the sheet exists and you can read it, and nothing more. So:

1. Attempt the operation and handle the outcome. Do not treat a read as a
   permission check for a write; it is not one. A read first is still worth it
   when you need the sheet's shape or row numbers anyway, or to fail early on
   an id that does not resolve.
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
can chain an export.

If you imported **only sources**, no run starts and the command succeeds with a
note. If you imported **questions** and no run starts within 120s, the command
fails: the run may just have been picked up late, and treating that as success
would export a sheet that is still being answered.

That error means the outcome is unknown, not that the import failed. Do **not**
export yet — an export now would report unanswered rows as if they were the
result. Poll `get-sheet` until the state settles on `IDLE` and the rows you
imported have answers, and only then export. Do not re-import either: the
questions are already on the sheet, so a second import starts no run and
returns the same error.

```bash
unique-cli agentic-table import mt_abc123 --question-file-id c_q --source-file-id c_src --wait
```

### Re-answer a single row

```bash
unique-cli agentic-table rerun-row <table_id> <row_order> [--wait] [--timeout <seconds>] [--start-timeout <seconds>]
```

Use this to redo one answer. **Re-importing a question will not redo it** —
import is delta-based and skips questions the sheet already has, so `rerun-row`
is the only way to re-answer an existing row.

`<row_order>` uses **the same numbering as `--row` on `get-cell`**: row 0 is the
header, data rows start at 1. So the row you inspected with
`get-cell --row 4` is the row you redo with `rerun-row <table_id> 4` — no
offset. Row 0 is rejected, since there is nothing to answer in a header.

Two kinds of refusal, which need different responses:

- **The row is not yours to redo.** A locked row, or one in a final review
  status, is declined because a person has settled that answer. Report it; do
  not look for a way around it.
- **Not now.** A rerun while the sheet is already processing is declined
  because only one run may be in flight. That clears by itself — wait for the
  current run to finish and try again.

A rerun always starts a run, so with `--wait` there is no benign "nothing
started" case: if no run appears within 120s the command fails.

```bash
unique-cli agentic-table rerun-row mt_abc123 4 --wait
```

To redo several rows, do them one at a time with `--wait`: the sheet takes one
run at a time, so a second `rerun-row` fired before the first finishes is
declined. There is no batch form. If most of the sheet needs redoing, consider
a fresh sheet instead.

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
body rather than as an HTTP error — so the steps chain with `&&`:

```bash
SHEET_JSON=$(unique-cli agentic-table create-sheet asst_123 --name "Vendor DDQ" --json) && \
SHEET=$(printf '%s' "$SHEET_JSON" | jq -r .sheetId) && \
unique-cli agentic-table import "$SHEET" --question-file-id c_questions --source-file-id c_sources --wait && \
unique-cli agentic-table export "$SHEET" --type FULL_REPORT --wait && \
unique-cli agentic-table get-sheet "$SHEET" --cells
```

Capture the JSON first and parse it in a second step, as above. Do **not** pipe
`create-sheet` directly into `jq`: an assignment takes the exit status of the
last command in the pipeline, so the CLI's failure is discarded, and because
errors go to stderr `jq` reads empty input and succeeds — leaving `$SHEET`
empty and the rest of the chain running against a sheet that does not exist.

To fill in an existing questionnaire from a sheet someone else has already
answered, skip the create and import steps: read the answers with
`get-sheet --cells` or `get-cell`, and use `cell-history` if you need to know
whether an answer came from a person or the assistant.

If a specific answer looks wrong or incomplete, fix that row with `rerun-row`
and export again, rather than re-importing the question or rebuilding the
sheet.

## Rules

1. Rows and columns are numbered from 0, and row 0 is the header — so the first
   question is row 1. This holds for `--row`/`--col` on `get-cell` and
   `cell-history` and for `<row_order>` on `rerun-row` alike; the same number
   means the same row in every command.
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
