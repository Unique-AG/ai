"""FastMCP server exposing schema-driven CRUD over an Excel-seeded SQLite DB."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from mcp_sqlite_excel import prompts
from mcp_sqlite_excel.db.repository import SqliteCrudRepository
from mcp_sqlite_excel.models import FieldMap, ServerStatus, ToolError
from mcp_sqlite_excel.settings import AppSettings, get_settings

settings = get_settings()
base_url = sys.argv[1] if len(sys.argv) > 1 else settings.base_url_env

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


def _build_mcp(cfg: AppSettings) -> FastMCP:
    if cfg.auth_disabled:
        return FastMCP("SQLite Excel CRUD")

    from fastmcp.server.auth.oauth_proxy import OAuthProxy
    from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier

    token_verifier = IntrospectionTokenVerifier(
        introspection_url=f"{cfg.zitadel_url}/oauth/v2/introspect",
        client_id=cfg.upstream_client_id,
        client_secret=cfg.upstream_client_secret,
        client_auth_method="client_secret_basic",
    )
    auth = OAuthProxy(
        upstream_authorization_endpoint=f"{cfg.zitadel_url}/oauth/v2/authorize",
        upstream_token_endpoint=f"{cfg.zitadel_url}/oauth/v2/token",
        upstream_client_id=cfg.upstream_client_id,
        upstream_client_secret=cfg.upstream_client_secret,
        upstream_revocation_endpoint=f"{cfg.zitadel_url}/oauth/v2/revoke",
        token_verifier=token_verifier,
        base_url=base_url,
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
    )
    return FastMCP("SQLite Excel CRUD", auth=auth)


mcp = _build_mcp(settings)


def _dump(model: BaseModel) -> str:
    return model.model_dump_json(indent=2)


def _tool_error(exc: Exception) -> str:
    return _dump(ToolError(error=type(exc).__name__, message=str(exc)))


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
) -> str:
    try:
        repo.ensure_ready()
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
async def reset_from_excel() -> str:
    try:
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
    if not Path(repo.excel_path).is_file():
        from mcp_sqlite_excel.scripts.generate_sample_excel import generate

        generate(Path(repo.excel_path))
    repo.ensure_ready()

    mcp.run(
        transport="http",
        host=settings.bind_host,
        port=settings.port,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
