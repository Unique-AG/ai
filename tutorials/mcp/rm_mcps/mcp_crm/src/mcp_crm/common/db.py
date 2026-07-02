"""common/db.py — shared PostgreSQL access + client resolution.

The same module ships in both servers (Advisory and CRM); they read the same
database (one short-lived read-only connection per call — the data is tiny, the
traffic low, and statelessness is the whole point of moving off n8n).

Storage convention for per-client read-only data: `<table>(client_id TEXT PK,
data JSONB)`. `data` is an OBJECT for "record" tools (returned spread as
`{client_id, **data}`) or an ARRAY for "list" tools (returned as
`{client_id, <field>: [...], count}`) — matching the n8n tool outputs exactly.
"""

import glob
import json
import os
import re
from pathlib import Path
from typing import Annotated, Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from pydantic import Field

from common.tool_prompts import tool_meta

load_dotenv()

DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_NAME = os.getenv("PGDATABASE", "mcpdb")
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASSWORD = os.getenv("PGPASSWORD", "postgres")

# Echoed when a client can't be resolved (mirrors the n8n CLIENT_ERROR_HINT).
CLIENT_ERROR_HINT = (
    "Unknown client. Use a name (Brunner, Hofer, Ellery, Lavanchy, Moretti-Conti) "
    "or client_id (PTY-0002005 / PTY-0002002 / PTY-0003001 / CH-PB-0049217 / "
    "CH-PB-0061884 / CH-PROS-0118; legacy numeric ids still resolve)."
)
NO_DATA = "No data for this client in this sub-source."


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


def _read(fn):
    conn = get_conn()
    conn.set_session(readonly=True)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            return fn(cur)
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    return _read(lambda cur: (cur.execute(sql, params), cur.fetchone())[1])


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    return _read(lambda cur: (cur.execute(sql, params), cur.fetchall())[1])


def execute(sql: str, params: tuple = ()) -> int:
    """Run a write statement (commit on success); return the affected row count
    (0 when nothing matched). Used by the editable client-memory tables."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.rowcount
    finally:
        conn.close()


# --- demo reset (mirrors mcp_trade_reconciliation's Reset_Demo_Data) ----------------------------
RESET_DEMO_DATA_DESCRIPTION = (
    "Reset this RM Agent MCP server's demo data to its baseline. This is a DESTRUCTIVE "
    "operation: it truncates this server's tables and re-inserts the original seed rows. Any "
    "changes made during the demo are discarded — in particular, on the CRM server the editable "
    "client memory (talking points / open questions / pinned documents) is restored to its "
    "original content (rows added during the demo are removed and deleted rows come back). Use "
    "this between demo runs to get a clean, predictable starting state."
)

_CREATE_TABLE_RE = re.compile(r"CREATE TABLE IF NOT EXISTS\s+\"?([A-Za-z_]\w*)\"?", re.IGNORECASE)


def reset_demo_data(sql_dir: str) -> dict:
    """Restore the demo to baseline by re-running every ``sql/*.sql`` seed file.

    Unlike a plain re-seed (the seeds use ``ON CONFLICT DO NOTHING``), this first
    TRUNCATEs the tables the seeds define, so edits/additions/deletions made during
    the demo are wiped and the original seed rows are restored. Runs in a single
    transaction; returns post-reset row counts per table.
    """
    files = sorted(glob.glob(os.path.join(sql_dir, "*.sql")))
    if not files:
        raise FileNotFoundError(f"No seed SQL files found in {sql_dir}")
    texts, tables = [], []
    for f in files:
        text = Path(f).read_text(encoding="utf-8")
        texts.append(text)
        tables.extend(_CREATE_TABLE_RE.findall(text))
    tables = list(dict.fromkeys(tables))  # de-dup, preserve order

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Truncate only the tables that already exist (handles a fresh DB too).
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = ANY(%s)",
                    (tables,),
                )
                existing = [r[0] for r in cur.fetchall()]
                if existing:
                    cur.execute("TRUNCATE TABLE " + ", ".join(existing) + " RESTART IDENTITY CASCADE")
                for text in texts:
                    # Execute each seed file as ONE multi-statement script: psycopg2 runs all
                    # ';'-separated statements via libpq in this transaction, and parses SQL
                    # quoting correctly. The files use no bound params, and several values
                    # contain ';' inside string literals (e.g. house_views), so a naive
                    # split(';') would corrupt them — whole-file execute is the safe choice.
                    cur.execute(text)
                counts = {}
                for tbl in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                    counts[tbl] = cur.fetchone()[0]
    finally:
        conn.close()
    return {
        "reset": True,
        "tables": counts,
        "total_rows": sum(counts.values()),
        "note": "Demo data restored to baseline.",
    }


# --- client resolution (name / legacy numeric / canonical id → canonical client_id) ------------
def resolve_client(value: str | None) -> str | None:
    if not value:
        return None
    row = query_one(
        "SELECT client_id FROM client_aliases WHERE alias = %s", (str(value).strip().lower(),)
    )
    return row["client_id"] if row else None


def unknown(value: str | None) -> dict[str, Any]:
    return {"client_id": value, "error": CLIENT_ERROR_HINT}


# --- per-client lookups (table name is a hardcoded constant, never user input) -----------------
def get_record(table: str, value: str | None) -> dict:
    cid = resolve_client(value)
    if cid is None:
        return unknown(value)
    row = query_one(f"SELECT data FROM {table} WHERE client_id = %s", (cid,))
    if row is None:
        return {"client_id": cid, "error": NO_DATA}
    data = row["data"]
    return {"client_id": cid, **data} if isinstance(data, dict) else {"client_id": cid, "items": data}


def get_list(table: str, value: str | None, field: str) -> dict:
    cid = resolve_client(value)
    if cid is None:
        return unknown(value)
    row = query_one(f"SELECT data FROM {table} WHERE client_id = %s", (cid,))
    items = row["data"] if row else []
    return {"client_id": cid, field: items, "count": len(items)}


# --- tool factory: build the standard per-client tools from a declarative spec -----------------
def make_client_tools(mcp, specs: list[dict]) -> None:
    """Register one MCP tool per spec. Each accepts `input` (name or client_id)
    and an optional `client_id`; `style` is 'record' or 'list' (with `field`)."""
    for spec in specs:
        _register_client_tool(mcp, spec)


def _register_client_tool(mcp, spec: dict) -> None:
    table = spec["table"]
    style = spec.get("style", "record")
    field = spec.get("field", "items")
    arg_desc = spec.get("arg_desc", "Client name or client_id.")

    def tool(
        input: Annotated[str, Field(description=arg_desc)] = "",
        client_id: Annotated[str, Field(description="Client id (alternative to input).")] = "",
    ) -> str:
        value = input or client_id
        result = get_record(table, value) if style == "record" else get_list(table, value, field)
        return json.dumps(result)

    tool.__name__ = spec["name"]
    mcp.tool(
        name=spec["name"],
        title=spec.get("title"),
        description=spec["description"],
        meta=tool_meta(spec["name"], spec.get("meta")),
    )(tool)
