"""FastMCP server exposing schema-driven CRUD over an Excel-seeded SQLite DB."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi.responses import JSONResponse
from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from unique_mcp.auth.zitadel.oidc_proxy import (
    ZitadelOIDCProxySettings,
    create_zitadel_oidc_proxy,
)
from unique_mcp.settings import ServerSettings

from mcp_sqlite_excel import prompts
from mcp_sqlite_excel.db.repository import SqliteCrudRepository
from mcp_sqlite_excel.models import FieldMap, ServerStatus, ToolError
from mcp_sqlite_excel.settings import AppSettings, get_settings

logger = logging.getLogger("mcp_sqlite_excel")

settings = get_settings()
server_settings = ServerSettings()

custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

repo = SqliteCrudRepository(settings=settings)


def _bind_host_and_port() -> tuple[str, int]:
    """Resolve listen address from UNIQUE_MCP_LOCAL_BASE_URL."""
    local = server_settings.local_base_url
    parsed = urlparse(str(local))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8004
    return host, port


def _allowed_hosts() -> list[str]:
    """Hostnames FastMCP may accept in the Host header (public URL + bind host).

    FastMCP's HostOriginGuard rejects unknown Host headers with HTTP 421. When
    bound to 0.0.0.0 behind Azure App Service, the public hostname must be
    allowlisted explicitly.
    """
    hosts: list[str] = []
    for url in (server_settings.public_base_url, server_settings.local_base_url):
        if url is None:
            continue
        hostname = urlparse(str(url)).hostname
        if hostname and hostname not in hosts:
            hosts.append(hostname)
    return hosts


def _build_mcp(cfg: AppSettings) -> FastMCP:
    if cfg.auth_disabled:
        logger.warning("AUTH_DISABLED=true — Zitadel OIDC is off (local demos only)")
        return FastMCP("SQLite Excel CRUD")

    oidc_proxy = create_zitadel_oidc_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oidc_proxy_settings=ZitadelOIDCProxySettings(),  # type: ignore[call-arg]
    )
    return FastMCP("SQLite Excel CRUD", auth=oidc_proxy)


mcp = _build_mcp(settings)


def _dump(model: BaseModel) -> str:
    return model.model_dump_json(indent=2)


def _tool_error(exc: Exception) -> str:
    return _dump(ToolError(error=type(exc).__name__, message=str(exc)))


async def _elicit_destructive_confirm(
    ctx: Context,
    *,
    message: str,
) -> bool:
    """Ask the client to confirm a destructive action via MCP elicitation.

    Returns True only when the user accepts and answers true/yes.
    """
    result = await ctx.elicit(message, response_type=bool)
    return result.action == "accept" and bool(result.data)


@mcp.tool(
    name="list_schema",
    title="List database schema",
    description=prompts.LIST_SCHEMA_DESCRIPTION,
    meta={
        "unique.app/icon": "database",
        "unique.app/system-prompt": prompts.LIST_SCHEMA_DESCRIPTION,
    },
)
async def list_schema() -> str:
    """Return tables and columns inferred from the Excel workbook / SQLite DB."""
    try:
        repo.ensure_ready()
        return _dump(repo.describe_schema())
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool(
    name="list_rows",
    title="List rows",
    description=prompts.LIST_ROWS_DESCRIPTION,
    meta={
        "unique.app/icon": "table",
        "unique.app/system-prompt": prompts.LIST_ROWS_DESCRIPTION,
    },
)
async def list_rows(
    table: Annotated[str, Field(description="Table name from list_schema (Excel sheet).")],
    filters: Annotated[
        dict[str, Any] | str | None,
        Field(
            default=None,
            description='Optional object of exact-match filters, e.g. {"ticker":"MSFT"}.',
        ),
    ] = None,
    limit: Annotated[int, Field(default=100, ge=1, le=2000)] = 100,
    offset: Annotated[int, Field(default=0, ge=0)] = 0,
) -> str:
    try:
        repo.ensure_ready()
        parsed = FieldMap.from_mcp_arg(filters, field_name="filters")
        return _dump(repo.list_rows(table, filters=parsed, limit=limit, offset=offset))
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool(
    name="get_row",
    title="Get row",
    description=prompts.GET_ROW_DESCRIPTION,
    meta={
        "unique.app/icon": "search",
        "unique.app/system-prompt": prompts.GET_ROW_DESCRIPTION,
    },
)
async def get_row(
    table: Annotated[str, Field(description="Table name from list_schema.")],
    row_id: Annotated[int | str, Field(description="Primary key value (id or row_id).")],
) -> str:
    try:
        repo.ensure_ready()
        return _dump(repo.get_row(table, row_id))
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool(
    name="create_row",
    title="Create row",
    description=prompts.CREATE_ROW_DESCRIPTION,
    meta={
        "unique.app/icon": "plus",
        "unique.app/system-prompt": prompts.CREATE_ROW_DESCRIPTION,
    },
)
async def create_row(
    table: Annotated[str, Field(description="Table name from list_schema.")],
    fields: Annotated[
        dict[str, Any] | str,
        Field(description='Object of column → value, e.g. {"ticker":"MSFT","direction":"Long"}.'),
    ],
) -> str:
    try:
        repo.ensure_ready()
        parsed = FieldMap.from_mcp_arg(fields, field_name="fields")
        return _dump(repo.create_row(table, parsed))
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool(
    name="update_row",
    title="Update row",
    description=prompts.UPDATE_ROW_DESCRIPTION,
    meta={
        "unique.app/icon": "pencil",
        "unique.app/system-prompt": prompts.UPDATE_ROW_DESCRIPTION,
    },
)
async def update_row(
    table: Annotated[str, Field(description="Table name from list_schema.")],
    row_id: Annotated[int | str, Field(description="Primary key value (id or row_id).")],
    fields: Annotated[
        dict[str, Any] | str,
        Field(description='Object of columns to update, e.g. {"direction":"Short"}.'),
    ],
) -> str:
    try:
        repo.ensure_ready()
        parsed = FieldMap.from_mcp_arg(fields, field_name="fields")
        return _dump(repo.update_row(table, row_id, parsed))
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool(
    name="delete_row",
    title="Delete row",
    description=prompts.DELETE_ROW_DESCRIPTION,
    meta={
        "unique.app/icon": "trash",
        "unique.app/system-prompt": prompts.DELETE_ROW_DESCRIPTION,
    },
)
async def delete_row(
    table: Annotated[str, Field(description="Table name from list_schema.")],
    row_id: Annotated[int | str, Field(description="Primary key value (id or row_id).")],
    ctx: Context,
) -> str:
    try:
        repo.ensure_ready()
        existing = repo.get_row(table, row_id)
        preview = _dump(existing)
        confirmed = await _elicit_destructive_confirm(
            ctx,
            message=(f"Delete row {row_id!r} from table `{table}`? This cannot be undone.\n\n{preview}"),
        )
        if not confirmed:
            return _dump(
                ToolError(
                    error="DeleteCancelled",
                    message=f"Deletion of {table!r} row {row_id!r} was cancelled.",
                )
            )
        return _dump(repo.delete_row(table, row_id))
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool(
    name="reset_from_excel",
    title="Reset database from Excel",
    description=prompts.RESET_FROM_EXCEL_DESCRIPTION,
    meta={
        "unique.app/icon": "refresh-cw",
        "unique.app/system-prompt": prompts.RESET_FROM_EXCEL_DESCRIPTION,
    },
)
async def reset_from_excel(ctx: Context) -> str:
    try:
        confirmed = await _elicit_destructive_confirm(
            ctx,
            message=(
                "Reset the SQLite database from the Excel workbook? "
                "All current rows will be deleted and replaced with seed data."
            ),
        )
        if not confirmed:
            return _dump(
                ToolError(
                    error="ResetCancelled",
                    message="Database reset was cancelled.",
                )
            )
        return _dump(repo.reset_from_excel())
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    status = ServerStatus(
        auth_disabled=settings.auth_disabled,
        db_path=repo.db_path,
        excel_path=repo.excel_path,
        tables=repo.list_tables() if repo.db_path.is_file() else [],
    )
    return JSONResponse(status.model_dump(mode="json"))


def main() -> None:
    logging.getLogger("mcp_sqlite_excel").setLevel(logging.DEBUG)

    if not Path(repo.excel_path).is_file():
        from mcp_sqlite_excel.scripts.generate_sample_excel import generate

        generate(Path(repo.excel_path))
    repo.ensure_ready()

    host, port = _bind_host_and_port()
    mcp.run(
        transport=server_settings.transport_scheme,
        host=host,
        port=port,
        log_level="debug",
        middleware=custom_middleware,
        allowed_hosts=_allowed_hosts(),
    )


if __name__ == "__main__":
    main()
