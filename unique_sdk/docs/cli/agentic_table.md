# Agentic Table

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

Read Agentic Table (magic table) sheets, cells, and cell history through the public magic-table API. These are **Tier 0** reads: they never write and never require confirmation. Every call is scoped to the configured user/company; sheet-role access (Owner / Can manage / Can edit) is enforced on the server, and a denial is reported as `agentic-table: permission denied`.

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
