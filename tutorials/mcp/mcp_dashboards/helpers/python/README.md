# mcp_dashboards — shared Python helpers

Reusable server-side machinery for TypeSpec-driven, Excel-backed FastMCP dataset
servers. This is the counterpart to [`helpers/astro/`](../astro/README.md): what
every dataset shares, as opposed to what each dataset writes for itself.

The split here is narrower than on the browser side, and deliberately so — see
[Why there is no shared CRUD layer](../../docs/architecture.md#why-there-is-no-shared-crud-layer).
A dataset's tools are the part that differs between datasets, so they are written
per dataset against generated Pydantic models. What this package provides is the
plumbing underneath them.

## Modules

| Module | What it is |
| --- | --- |
| `settings.py` | `AppSettings` — Excel and SQLite paths plus transport binding, via pydantic-settings |
| `db/repository.py` | `SqliteCrudRepository` — allowlisted SQL over one Excel-seeded database |
| `db/excel_loader.py` | Workbook reading, header detection, type inference, and the `create_table` / `insert_rows` primitives dataset import plans build on |
| `models.py` | Storage-level Pydantic models: `TableSchema`, `ColumnInfo`, `ListRowsResult`, `CountByResult`, `RowResult`, `ServerStatus`, and friends |
| `tools.py` | `tool_errors` — logs a full traceback and re-raises as a FastMCP `ToolError` |
| `binding.py` | `enrich_binding_row` / `flatten_dotted_paths` — nested domain rows plus flat dotted keys for the Unique platform iframe host (see [dom-contract.md](../../docs/dom-contract.md#platform-row-shape-vs-live-local)) |
| `elicitation.py` | `elicit_confirm` and `elicit_form` for interactive MCP prompts |

Note that `models.py` holds *storage*-level models. A dataset's public domain
models are generated from its TypeSpec contract into
`datasets/<name>/fastmcp/generated/models.py` and are never hand-written.

`elicitation.py` is used by account_review `update_client` (status confirm),
`draft_client_email`, and `send_email` (draft form; send also confirms delivery).
The `live-local` host renders the modal.

## Settings

A dataset server constructs `AppSettings` with dataset-local path defaults, but
only when the matching env vars are unset — so Azure can override
`SQLITE_PATH=/home/data/...` without losing local isolation:

```python
kwargs = {}
if "EXCEL_PATH" not in os.environ:
    kwargs["excel_path"] = DATASET_ROOT / "data" / "account_review_dataset.xlsx"
if "SQLITE_PATH" not in os.environ:
    kwargs["sqlite_path"] = DATASET_ROOT / "data" / "account_review.sqlite"
settings = AppSettings(**kwargs)
```

Pydantic-settings ranks constructor arguments above environment variables, so
never pass `excel_path=` / `sqlite_path=` when you want `EXCEL_PATH` /
`SQLITE_PATH` to win. `host`, `port`, `auth_disabled`, and the header detection
knobs also read from the environment.

## Repository

`SqliteCrudRepository` is schema-aware rather than generic. Table and column
names are validated against the real schema before they reach SQL, so a tool can
accept a column name from a caller without opening an injection path.

Three behaviours are worth knowing about when writing a server against it:

- **Schema caching.** Table names and schemas are read once and cached, since
  they are fixed after bootstrap. Anything that recreates tables must call
  `invalidate_schema_cache()`; `ensure_ready()` and `reset_from_excel()` already
  do.
- **Batched reads.** `list_rows_where_in()` fetches child rows for a whole page
  of parents in one query. Use it instead of looping — that loop is how the
  reference dataset originally ended up issuing one query per row.
- **Foreign keys are enforced.** `PRAGMA foreign_keys = ON` is set per
  connection, so a dataset that declares `REFERENCES` in its import plan gets
  cascade behaviour rather than silent orphans.

Bootstrapping is the intended extension point. A dataset subclasses the
repository and overrides `ensure_ready` and `reset_from_excel` to call its own
import plan, inheriting everything else:

```python
class AccountReviewRepository(SqliteCrudRepository):
    def ensure_ready(self) -> None:
        if self._ready:
            return
        if not self.db_path.is_file() or not self._has_account_review_shape():
            bootstrap_account_review_from_excel(...)
            self.invalidate_schema_cache()
        self._ready = True
```

Doing this once per process matters: an earlier version re-read the table schema
on every tool call just to confirm a few column names still existed.

## Error handling

Tools return only their domain model, and failures travel as protocol-level MCP
errors rather than as a success payload with an `error` key the caller has to
sniff for. `tool_errors` does that translation:

```python
@mcp.tool
@tool_errors(logger)
def list_clients(...) -> ClientListResult:
    ...
```

Tools are written as plain `def`, not `async def`. FastMCP offloads synchronous
tools to a thread pool, so blocking SQLite calls stay off the event loop; making
them `async` would block it.

## Development

```bash
uv run pytest                      # from helpers/python
uv run --project helpers/python python datasets/account_review/fastmcp/server.py
```

The second command is run from the `mcp_dashboards` root and is how a dataset
server is started for `live-local` dashboard work.
