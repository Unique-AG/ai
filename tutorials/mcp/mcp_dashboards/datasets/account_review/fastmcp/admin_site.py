"""HTTP admin UI + REST API for browsing/editing the account_review SQLite DB.

Served from the same FastMCP process as the MCP tools so Azure exposes both at
one hostname: `/` (UI), `/api/*` (CRUD + reset), `/mcp` (protocol).
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from mcp_dashboards.db.repository import SqliteCrudRepository
from mcp_dashboards.models import ServerStatus
from mcp_dashboards.settings import AppSettings
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("account_review_mcp.admin")

STATIC_DIR = Path(__file__).resolve().parent / "static"
ADMIN_HTML = STATIC_DIR / "admin.html"

MAX_PAGE_SIZE = 500


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _parse_row_id(raw: str) -> int | str:
    try:
        return int(raw)
    except ValueError:
        return raw


def register_admin_routes(
    mcp: FastMCP,
    *,
    repo: SqliteCrudRepository,
    settings: AppSettings,
    dataset: str = "account_review",
) -> None:
    """Attach admin HTML and `/api/*` CRUD routes to `mcp`."""

    @mcp.custom_route("/", methods=["GET"])
    async def admin_index(request: Request) -> Response:  # noqa: ARG001
        if not ADMIN_HTML.is_file():
            return _error(500, f"admin UI missing at {ADMIN_HTML}")
        return FileResponse(ADMIN_HTML, media_type="text/html; charset=utf-8")

    @mcp.custom_route("/api/status", methods=["GET"])
    async def api_status(request: Request) -> JSONResponse:  # noqa: ARG001
        tables: list[str] = []
        if repo.db_path.is_file():
            tables = repo.list_tables()
        status = ServerStatus(
            dataset=dataset,
            db_path=repo.db_path,
            excel_path=repo.excel_path,
            tables=tables,
        )
        payload = status.model_dump(mode="json")
        payload["auth_disabled"] = settings.auth_disabled
        return JSONResponse(payload)

    @mcp.custom_route("/api/schema", methods=["GET"])
    async def api_schema(request: Request) -> JSONResponse:  # noqa: ARG001
        repo.ensure_ready()
        return JSONResponse(repo.describe_schema().model_dump(mode="json"))

    @mcp.custom_route("/api/tables/{table}/rows", methods=["GET"])
    async def api_list_rows(request: Request) -> JSONResponse:
        table = request.path_params["table"]
        try:
            limit = min(
                MAX_PAGE_SIZE, max(1, int(request.query_params.get("limit", "50")))
            )
            offset = max(0, int(request.query_params.get("offset", "0")))
        except ValueError:
            return _error(400, "limit and offset must be integers")
        search = request.query_params.get("search") or None
        repo.ensure_ready()
        try:
            result = repo.list_rows(table, search=search, limit=limit, offset=offset)
        except KeyError as exc:
            return _error(404, str(exc))
        except ValueError as exc:
            return _error(400, str(exc))
        return JSONResponse(result.model_dump(mode="json"))

    @mcp.custom_route("/api/tables/{table}/rows/{row_id}", methods=["GET"])
    async def api_get_row(request: Request) -> JSONResponse:
        table = request.path_params["table"]
        row_id = _parse_row_id(request.path_params["row_id"])
        repo.ensure_ready()
        try:
            result = repo.get_row(table, row_id)
        except KeyError as exc:
            return _error(404, str(exc))
        return JSONResponse(result.model_dump(mode="json"))

    @mcp.custom_route("/api/tables/{table}/rows", methods=["POST"])
    async def api_create_row(request: Request) -> JSONResponse:
        table = request.path_params["table"]
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return _error(400, "JSON body required")
        fields = body.get("fields") if isinstance(body, dict) else None
        if not isinstance(fields, dict):
            return _error(400, 'body must be {"fields": {...}}')
        repo.ensure_ready()
        try:
            result = repo.create_row(table, fields)
        except KeyError as exc:
            return _error(404, str(exc))
        except ValueError as exc:
            return _error(400, str(exc))
        logger.info("admin create table=%s", table)
        return JSONResponse(result.model_dump(mode="json"), status_code=201)

    @mcp.custom_route("/api/tables/{table}/rows/{row_id}", methods=["PATCH"])
    async def api_update_row(request: Request) -> JSONResponse:
        table = request.path_params["table"]
        row_id = _parse_row_id(request.path_params["row_id"])
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return _error(400, "JSON body required")
        fields = body.get("fields") if isinstance(body, dict) else None
        if not isinstance(fields, dict):
            return _error(400, 'body must be {"fields": {...}}')
        repo.ensure_ready()
        try:
            result = repo.update_row(table, row_id, fields)
        except KeyError as exc:
            return _error(404, str(exc))
        except ValueError as exc:
            return _error(400, str(exc))
        logger.info(
            "admin update table=%s row_id=%s fields=%s", table, row_id, list(fields)
        )
        return JSONResponse(result.model_dump(mode="json"))

    @mcp.custom_route("/api/tables/{table}/rows/{row_id}", methods=["DELETE"])
    async def api_delete_row(request: Request) -> JSONResponse:
        table = request.path_params["table"]
        row_id = _parse_row_id(request.path_params["row_id"])
        repo.ensure_ready()
        try:
            result = repo.delete_row(table, row_id)
        except KeyError as exc:
            return _error(404, str(exc))
        logger.info("admin delete table=%s row_id=%s", table, row_id)
        return JSONResponse(result.model_dump(mode="json"))

    @mcp.custom_route("/api/reset", methods=["POST"])
    async def api_reset(request: Request) -> JSONResponse:  # noqa: ARG001
        repo.ensure_ready()
        summary = repo.reset_from_excel()
        logger.warning("admin reset_from_excel db=%s", repo.db_path)
        return JSONResponse(summary.model_dump(mode="json"))
