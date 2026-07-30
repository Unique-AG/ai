# Agentic Table

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

Work with Agentic Table (magic table) sheets through the public magic-table API. The **read** commands (`get-sheet`, `get-cell`, `cell-history`, `list-exports`) are **Tier 0**: they never write and never require confirmation. The **write** commands (`create-sheet`, `import`, `export`) drive the full loop — create a sheet, populate it, run the agent, and export the answers. Every call is scoped to the configured user/company; sheet-role access (Owner / Can manage / Can edit) is enforced on the server, and a denial is reported as `agentic-table: permission denied`.

## agentic-table get-sheet

Show a sheet summary: name, state, and row count. Add `--metadata` for sheet-level metadata entries and `--cells` to include cell values.

**Synopsis:**

```
agentic-table get-sheet <table_id> [--cells] [--metadata] [--json]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `table_id` | The magic-table sheet id |

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--cells` | Include cell values in the output | off |
| `--metadata` | Include sheet-level metadata entries | off |
| `--json` | Print the raw sheet JSON | off |

**Example:**

```bash
unique-cli agentic-table get-sheet mt_abc123 --metadata
```

```
Sheet:       Due Diligence Q1
ID:          mt_abc123
State:       IDLE
Rows:        3
Created by:  user_abc
Created:     2026-01-01 00:00

Metadata:
  region:  EU
```

---

## agentic-table get-cell

Show a single cell by its row and column order.

**Synopsis:**

```
agentic-table get-cell <table_id> --row <N> --col <N> [--json]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--row` | Row order (0-based, required) |
| `--col` | Column order (0-based, required) |
| `--json` | Print the raw cell JSON |

**Example:**

```bash
unique-cli agentic-table get-cell mt_abc123 --row 1 --col 2
```

```
Sheet:   mt_abc123
Row:     1
Column:  2
Locked:  no

Text:
The management fee is 2%.
```

---

## agentic-table cell-history

Show a single cell's log/edit history: each entry's timestamp, actor, source message id, and the logged text recorded by prior edits.

**Synopsis:**

```
agentic-table cell-history <table_id> --row <N> --col <N> [--json]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--row` | Row order (0-based, required) |
| `--col` | Column order (0-based, required) |
| `--json` | Print the raw log entries as JSON |

**Example:**

```bash
unique-cli agentic-table cell-history mt_abc123 --row 1 --col 2
```

```
Cell history (row 1, col 2) — 1 entry

- 2026-01-02 09:30  ASSISTANT  [msg_9]
    Answered from source [source1]
```

---

## agentic-table list-exports

List a sheet's export artifacts (full report, question export, agentic report). `CONTENT` is populated once an artifact reaches the `DONE` state; pending artifacts show `-`.

**Synopsis:**

```
agentic-table list-exports <table_id> [--json]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Print the raw artifact list as JSON |

**Example:**

```bash
unique-cli agentic-table list-exports mt_abc123
```

```
2 export artifact(s):

TYPE         STATE        ID          CONTENT       UPDATED
FULL_REPORT  DONE         artifact_1  cont_export   2026-01-01 00:01
QUESTIONS    IN_PROGRESS  artifact_2  -             2026-01-01 00:00
```

---

## agentic-table create-sheet

Create a new, empty sheet in a space. The printed `ID` is the `table_id` used by every other command.

**Synopsis:**

```
agentic-table create-sheet <assistant_id> [--name <name>] [--due-at <iso8601>] [--json]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `assistant_id` | The space (assistant) the sheet is created in; you must have write access |

**Options:**

| Option | Description |
|--------|-------------|
| `--name` | Sheet name |
| `--due-at` | Due date (ISO-8601, e.g. `2026-12-31T00:00:00Z`) |
| `--json` | Print the raw sheet JSON |

**Example:**

```bash
unique-cli agentic-table create-sheet asst_123 --name "Vendor DDQ"
```

```
Sheet:             Vendor DDQ
ID:                mt_abc123
Due diligence ID:  dd_1
State:             IDLE
Created by:        user_abc
Created:           2026-01-01 00:00
```

---

## agentic-table import

Import questions and/or source files into a sheet. Adding **new questions** (file ids or texts) triggers the agent run; adding only sources does not. Ids/texts already on the sheet are skipped. The call is rejected while the sheet is already processing.

With `--wait`, the command blocks until the triggered run finishes (or `--timeout` elapses) so you can chain an `export`.

A run leaves no durable record of itself, so the wait has to catch the sheet in `PROCESSING`. A very short run can pass through between two polls; polling is dense over the opening seconds to narrow that window, but it cannot close it — that needs a per-run signal the public API does not expose yet ([UN-23683](https://unique-ch.atlassian.net/browse/UN-23683)). Transient read failures during the wait are retried, since the import itself has already been accepted by then.

What happens when no run is observed depends on what you submitted. A sources-only import never starts one, so that is reported as a note and the command succeeds. If you submitted questions, a run was expected — not seeing one within 120s is treated as an error, because the pickup may simply be late and exiting 0 would let a `&&` chain export a sheet that is still being answered. The outcome is then unknown rather than failed: poll `get-sheet` until the state settles on `IDLE` and the imported rows carry answers, and export only after that. Exporting straight away would report unanswered rows as the result. Re-importing is not the answer either — questions the sheet already has produce the same error: also a no-op, but not one the command can tell apart from a late pickup.

**Synopsis:**

```
agentic-table import <table_id> [--question-file-id <id>]... [--question-text <text>]...
                                [--source-file-id <id>]... [--context <text>]
                                [--wait] [--timeout <seconds>] [--start-timeout <seconds>] [--json]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--question-file-id` | Content id of a questionnaire file (repeatable) | |
| `--question-text` | A question to add directly (repeatable) | |
| `--source-file-id` | Content id of a source/knowledge file (repeatable) | |
| `--context` | Free-text context for the run | |
| `--wait` | Wait for the triggered run to finish | off |
| `--timeout` | Max seconds to wait when `--wait` is set | 600 |
| `--start-timeout` | Max seconds to wait for the run to be picked up, before treating it as never started. Counts against `--timeout`. Raise it when the worker queue is slow | 120 |
| `--json` | Print raw JSON. `--wait` adds `runStarted` and `finalState` alongside `result` | off |

**Example:**

```bash
unique-cli agentic-table import mt_abc123 --question-file-id c_q --source-file-id c_src --wait
```

```
Action:  import
Result:  OK
Detail:  accepted
Run finished (state: IDLE).
```

---

## agentic-table rerun-row

Re-run the agent for a single row. This is the only way to redo one answer: `import` is delta-based and skips questions the sheet already has, so it will not re-answer an existing row.

`<row_order>` is the same number `get-cell --row` takes: row 0 is the header, so answerable rows start at 1. `get-cell --row 4` and `rerun-row <table_id> 4` address the same row — there is no offset between the two commands. Values below 1 are rejected by the CLI before the request is made, since a rerun is an audited write and there is no point spending an audit entry on input that cannot be valid.

The backend declines a row that is locked or in a final review status — a person has settled that answer — and also declines any rerun while the sheet is already processing, which is transient and clears once the current run finishes.

Like the whole-sheet run, a rerun is asynchronous. With `--wait`, the command polls until the sheet leaves `PROCESSING`. Unlike `import`, a rerun always triggers a run, so there is no benign "nothing started" case — not observing one within the start window is an error.

Two limits worth knowing. A rerun is the fastest operation in the system, so it can finish between two polls and be reported as never observed; the error text says so, and `cell-history` on the row settles it. And the wait watches *sheet* state, so on a shared sheet it cannot tell your rerun from a run someone else started. Both need a row-level signal the API does not expose yet ([UN-23683](https://unique-ch.atlassian.net/browse/UN-23683)).

To redo several rows, run them one at a time with `--wait`: the sheet accepts one run at a time, so a second `rerun-row` issued before the first finishes is declined. There is no batch form.

**Synopsis:**

```
agentic-table rerun-row <table_id> <row_order> [--wait] [--timeout <seconds>] [--start-timeout <seconds>] [--json]
```

**Options:**

| Option | Description | Default |
| --- | --- | --- |
| `--wait` | Wait for the triggered rerun to finish | off |
| `--timeout` | Max seconds to wait when `--wait` is set | 600 |
| `--start-timeout` | Max seconds to wait for the rerun to be picked up, before treating it as never started. Counts against `--timeout` | 120 |
| `--json` | Print raw JSON. `--wait` adds `rowOrder` and `finalState` alongside `result` | off |

**Example:**

```bash
unique-cli agentic-table rerun-row mt_abc123 4 --wait
```

```
Action:  rerun
Result:  OK
Detail:  accepted
Row 4 rerun finished (state: IDLE).
```

---

## agentic-table export

Generate export artifacts (`FULL_REPORT`, `QUESTIONS`, `AGENTIC_REPORT`). Generation is asynchronous. With `--wait`, the command polls until each requested type is `DONE` and prints the artifact table with the `contentId` to download; an artifact entering `ERROR` fails fast.

**Synopsis:**

```
agentic-table export <table_id> --type <TYPE>... [--wait] [--timeout <seconds>] [--json]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--type` | Artifact type: `FULL_REPORT`, `QUESTIONS`, or `AGENTIC_REPORT` (repeatable, required) | |
| `--wait` | Wait for the requested artifacts to be ready, then list them | off |
| `--timeout` | Max seconds to wait when `--wait` is set | 600 |
| `--json` | Print raw JSON. `--wait` adds `artifacts` alongside `result` | off |

**Example:**

```bash
unique-cli agentic-table export mt_abc123 --type FULL_REPORT --wait
```

```
Action:  export
Result:  OK
1 export artifact(s):

TYPE         STATE  ID           CONTENT      UPDATED
FULL_REPORT  DONE   artifact_1   cont_export  2026-01-01 00:01
```

---

## Full-loop recipe

Create a sheet, populate and run it, then export the answers. Every step exits non-zero on failure — including a rejection the backend reports in the response body rather than as an HTTP error — so the steps can be chained with `&&`:

```bash
SHEET_JSON=$(unique-cli agentic-table create-sheet asst_123 --name "Vendor DDQ" --json) && \
SHEET=$(printf '%s' "$SHEET_JSON" | jq -r .sheetId) && \
unique-cli agentic-table import "$SHEET" --question-file-id c_questions --source-file-id c_sources --wait && \
unique-cli agentic-table export "$SHEET" --type FULL_REPORT --wait && \
unique-cli agentic-table get-sheet "$SHEET" --cells
```

Capture the JSON and parse it in two steps rather than piping `create-sheet` straight into `jq`. A shell assignment takes the exit status of the last command in the pipeline, so `SHEET=$(unique-cli ... | jq ...)` reports `jq`'s status and discards the CLI's. Errors go to stderr, so `jq` would read empty input, print nothing and succeed — leaving `$SHEET` empty and the `&&` chain running on against a sheet that was never created. Splitting the assignment puts the CLI's own exit status back in the chain. `set -o pipefail` also works if the recipe runs inside a script you control.

Read the produced answers with `get-sheet --cells` / `get-cell` and download an export via the Content API using the `contentId` shown by `export` / `list-exports`.
