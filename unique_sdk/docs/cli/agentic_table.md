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

With `--wait`, the command blocks until the triggered run finishes (or `--timeout` elapses) so you can chain an `export`. If only sources were added (no run started), that is reported as a note, not an error.

**Synopsis:**

```
agentic-table import <table_id> [--question-file-id <id>]... [--question-text <text>]...
                                [--source-file-id <id>]... [--context <text>]
                                [--wait] [--timeout <seconds>] [--json]
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
| `--json` | Print raw JSON | off |

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
| `--json` | Print raw JSON | off |

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

Create a sheet, populate and run it, then export the answers. Because every step exits non-zero on failure — including a rejection the backend reports in the response body rather than as an HTTP error — the steps can be chained with `&&`:

```bash
SHEET=$(unique-cli agentic-table create-sheet asst_123 --name "Vendor DDQ" --json | jq -r .sheetId) && \
unique-cli agentic-table import "$SHEET" --question-file-id c_questions --source-file-id c_sources --wait && \
unique-cli agentic-table export "$SHEET" --type FULL_REPORT --wait && \
unique-cli agentic-table get-sheet "$SHEET" --cells
```

Read the produced answers with `get-sheet --cells` / `get-cell` and download an export via the Content API using the `contentId` shown by `export` / `list-exports`.
