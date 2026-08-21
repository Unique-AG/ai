"""
Risk Database MCP — read-only query tools over a bundled Excel risk database.
Loads sheets into pandas at startup; mirrors them to PostgreSQL when configured;
exposes get_schema and query_data. HTTP transport with Zitadel OAuth (FastMCP OAuthProxy).
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier
from key_value.aio.stores.filetree import FileTreeStore
from key_value.aio.stores.postgresql import PostgreSQLStore
from sqlalchemy import create_engine
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

logger = logging.getLogger("risk-database-mcp")
logging.basicConfig(level=logging.INFO)

ZITADEL_URL = os.getenv("ZITADEL_URL", "https://id.unique.app")
upstream_client_id = os.getenv("UPSTREAM_CLIENT_ID", "default_client_id")
upstream_client_secret = os.getenv("UPSTREAM_CLIENT_SECRET", "default_client_secret")
base_url_env = os.getenv("BASE_URL_ENV", "http://127.0.0.1:8002")
base_url_arg = sys.argv[1] if len(sys.argv) > 1 else base_url_env

SHEETS: dict[str, pd.DataFrame] = {}
DATA_PATH = Path(__file__).resolve().parent / "data" / "risk_database.xlsx"
VALID_SHEETS: list[str] = []


def load_data() -> None:
    global VALID_SHEETS
    xlsx = pd.ExcelFile(DATA_PATH)
    for name in xlsx.sheet_names:
        SHEETS[name] = pd.read_excel(xlsx, sheet_name=name)
    VALID_SHEETS = [n for n in SHEETS if n != "schema"]


def _sanitize_table_name(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "sheet"
    if s[0].isdigit():
        s = f"t_{s}"
    return s


def _build_postgresql_store_url() -> str | None:
    if not os.getenv("PGHOST"):
        return None
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "")
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE", "riskdb")
    sslmode = os.getenv("PG_SSLMODE", "require" if "azure" in host.lower() else "")
    auth = f"{quote_plus(user)}:{quote_plus(password)}"
    base = f"postgresql://{auth}@{host}:{port}/{database}"
    if sslmode:
        return f"{base}?sslmode={sslmode}"
    return base


def _build_sqlalchemy_sync_url() -> str | None:
    """SQLAlchemy URL for pandas.to_sql (psycopg2)."""
    override = os.getenv("PG_SYNC_URL")
    if override:
        return override
    store_url = _build_postgresql_store_url()
    if not store_url:
        return None
    u = store_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if u.startswith("postgresql://"):
        return u.replace("postgresql://", "postgresql+psycopg2://", 1)
    return None


def sync_excel_to_postgres() -> None:
    """Recreate all sheet tables in Postgres from in-memory SHEETS (mirrors Excel)."""
    url = _build_sqlalchemy_sync_url()
    if not url:
        logger.info("Postgres not configured (PGHOST); skipping mirror sync.")
        return
    try:
        engine = create_engine(url)
        for sheet_name, df in SHEETS.items():
            table = _sanitize_table_name(sheet_name)
            df.to_sql(table, engine, if_exists="replace", index=False)
            logger.info("Synced sheet %r -> table %r (%s rows)", sheet_name, table, len(df))
        engine.dispose()
        logger.info("Postgres mirror sync complete.")
    except Exception:
        logger.exception("Postgres mirror sync failed; MCP tools still use Excel/pandas.")


_pg_store_url = _build_postgresql_store_url()
if _pg_store_url:
    _client_storage = PostgreSQLStore(url=_pg_store_url)
else:
    local_storage_path = Path(
        os.getenv(
            "LOCAL_OAUTH_STORAGE_PATH",
            str(Path(__file__).resolve().parent / ".local" / "oauth-client-store"),
        )
    )
    _client_storage = FileTreeStore(data_directory=local_storage_path)

token_verifier = IntrospectionTokenVerifier(
    introspection_url=f"{ZITADEL_URL}/oauth/v2/introspect",
    client_id=upstream_client_id,
    client_secret=upstream_client_secret,
    client_auth_method="client_secret_basic",
)

auth = OAuthProxy(
    upstream_authorization_endpoint=f"{ZITADEL_URL}/oauth/v2/authorize",
    upstream_token_endpoint=f"{ZITADEL_URL}/oauth/v2/token",
    upstream_client_id=upstream_client_id,
    upstream_client_secret=upstream_client_secret,
    upstream_revocation_endpoint=f"{ZITADEL_URL}/oauth/v2/revoke",
    token_verifier=token_verifier,
    base_url=base_url_arg,
    redirect_path=None,
    issuer_url=None,
    service_documentation_url=None,
    allowed_client_redirect_uris=None,
    valid_scopes=[
        "mcp:tools",
        "mcp:prompts",
        "mcp:resources",
        "mcp:resource-templates",
        "email",
        "openid",
        "profile",
    ],
    forward_pkce=True,
    token_endpoint_auth_method="client_secret_post",
    extra_authorize_params=None,
    extra_token_params=None,
    client_storage=_client_storage,
)

custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

mcp = FastMCP("risk-database-mcp", auth=auth)


def _apply_filter(df: pd.DataFrame, col: str, val: object) -> pd.DataFrame:
    if col not in df.columns:
        return df
    if isinstance(val, dict) and "op" in val and "value" in val:
        op, v = val["op"], val["value"]
        s = df[col]
        if op == "contains":
            mask = s.astype(str).str.contains(str(v), case=False, na=False, regex=False)
        elif op in ("gt", "gte", "lt", "lte"):
            num_s = pd.to_numeric(s, errors="coerce")
            num_v = float(v) if isinstance(v, str) else v
            if op == "gt":
                mask = num_s > num_v
            elif op == "gte":
                mask = num_s >= num_v
            elif op == "lt":
                mask = num_s < num_v
            else:
                mask = num_s <= num_v
        elif op == "between" and isinstance(v, (list, tuple)) and len(v) == 2:
            low = float(v[0]) if isinstance(v[0], str) else v[0]
            high = float(v[1]) if isinstance(v[1], str) else v[1]
            num = pd.to_numeric(s, errors="coerce")
            mask = (num >= low) & (num <= high)
        else:
            mask = s.astype(str).str.lower() == str(v).lower()
        return df[mask]
    return df[df[col].astype(str).str.lower() == str(val).lower()]


GET_SCHEMA_DESCRIPTION = """Get schema of all available risk database sheets.

Returns for each sheet: name, row count, column list, primary key (from schema meta), and 2 sample rows.
Call this first to understand what data is available, then use query_data to filter and fetch rows.

Sheets include: positions, exposures, pnl_daily, factor_risk, var_stress, liquidity, risk_limits, drawdowns, counterparty, performance, events_calendar, crowding, correlations, greeks, redemption_liquidity."""


QUERY_DATA_DESCRIPTION = """Query any sheet in the risk database with optional filters.

- sheet_name: one of the 15 data sheet names (e.g. positions, exposures, pnl_daily, risk_limits, liquidity).
- filters: optional dict. For exact match use { "column_name": value }. For advanced use { "column_name": { "op": "contains"|"gt"|"lt"|"gte"|"lte"|"between", "value": ... } }. For "between", value must be [low, high].
- Comparison operators and "between" are numeric only. For dates, use exact matches or fetch the rows and filter/sort dates yourself.
- columns: optional list of column names to return (default: all).
- limit: max rows to return (default 50).

Anomalies / flags (no calculation, query only): use filters to get flagged rows, e.g. risk_limits with breach_flag=1, liquidity with illiquid_flag=1, crowding with crowding_tier='CRITICAL'. These are pre-computed flags in the data."""


@mcp.tool(description=GET_SCHEMA_DESCRIPTION)
async def get_schema() -> str:
    if not SHEETS:
        return "Data not loaded."
    parts = []
    schema_df = SHEETS.get("schema")
    for name in VALID_SHEETS:
        df = SHEETS[name]
        info = f"## {name} ({len(df)} rows)\n"
        if schema_df is not None and "primary_key" in schema_df.columns:
            row = schema_df[schema_df["sheet_name"] == name]
            if not row.empty:
                info += f"Primary key: {row['primary_key'].iloc[0]}\n"
        info += f"Columns: {', '.join(df.columns)}\n"
        info += df.head(2).to_markdown(index=False)
        parts.append(info)
    return "\n\n".join(parts)


@mcp.tool(description=QUERY_DATA_DESCRIPTION)
async def query_data(
    sheet_name: str,
    filters: dict | None = None,
    columns: list[str] | None = None,
    limit: int = 50,
) -> str:
    if sheet_name not in SHEETS or sheet_name == "schema":
        return f"Unknown sheet: {sheet_name}. Use get_schema to list valid sheet names."
    df = SHEETS[sheet_name].copy()
    if filters:
        for col, val in filters.items():
            df = _apply_filter(df, col, val)
    if columns:
        missing = [c for c in columns if c not in df.columns]
        if missing:
            return f"Unknown columns: {missing}. Available: {', '.join(df.columns)}"
        df = df[columns]
    total = len(df)
    df = df.head(limit)
    result = df.to_markdown(index=False)
    if total > limit:
        result += f"\n\n(Showing {limit} of {total} rows)"
    return result


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request) -> JSONResponse:
    return JSONResponse({"server": "running", "name": "risk-database-mcp"})


load_data()
print("Loaded data from Excel")
sync_excel_to_postgres()
print("Synced data to Postgres")

port = int(os.environ.get("PORT", os.environ.get("WEBSITES_PORT", "8002")))

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
        log_level=os.getenv("LOG_LEVEL", "debug"),
        middleware=custom_middleware,
    )
