"""HTTP admin UI + REST API for browsing/editing the account_review SQLite DB.

Served from the same FastMCP process as the MCP tools so Azure exposes both at
one hostname: `/` (UI), `/api/*` (CRUD + reset), `/mcp` (protocol).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

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

# 1:1 satellite tables (and clients) editable in the by-client UI.
CLIENT_SECTIONS = (
    "clients",
    "contacts",
    "portfolios",
    "compliance",
    "review_schedules",
    "suitability",
    "case_actions",
)


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _parse_row_id(raw: str) -> int | str:
    try:
        return int(raw)
    except ValueError:
        return raw


def _list_client_summaries(repo: Any, *, search: str | None, limit: int, offset: int):
    list_fn = getattr(repo, "list_client_rows", None)
    if list_fn is None:
        raise TypeError("repository does not support list_client_rows")
    result = list_fn(
        search=search,
        search_fields=["identity_name", "identity_reference", "case_action_status"],
        limit=limit,
        offset=offset,
    )
    summaries = [
        {
            "id": row["id"],
            "name": row.get("identity_name"),
            "reference": row.get("identity_reference"),
            "segment": row.get("identity_segment"),
            "status": row.get("case_action_status"),
            "risk_level": row.get("compliance_risk_level"),
        }
        for row in result.rows
    ]
    return {
        "count": result.count,
        "total_matching": result.total_matching,
        "limit": result.limit,
        "offset": result.offset,
        "search": result.search,
        "rows": summaries,
    }


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

    @mcp.custom_route("/api/clients", methods=["GET"])
    async def api_list_clients(request: Request) -> JSONResponse:
        """Sidebar list: identity + status summaries from the joined client view."""
        try:
            limit = min(
                MAX_PAGE_SIZE, max(1, int(request.query_params.get("limit", "100")))
            )
            offset = max(0, int(request.query_params.get("offset", "0")))
        except ValueError:
            return _error(400, "limit and offset must be integers")
        search = request.query_params.get("search") or None
        repo.ensure_ready()
        try:
            payload = _list_client_summaries(
                repo, search=search, limit=limit, offset=offset
            )
        except (TypeError, ValueError) as exc:
            return _error(400, str(exc))
        return JSONResponse(payload)

    @mcp.custom_route("/api/clients/{client_id}", methods=["GET"])
    async def api_get_client(request: Request) -> JSONResponse:
        """Full editable bundle: each 1:1 section + figure_metrics rows."""
        client_id = _parse_row_id(request.path_params["client_id"])
        if not isinstance(client_id, int):
            return _error(400, "client_id must be an integer")
        repo.ensure_ready()
        get_bundle = getattr(repo, "get_client_bundle", None)
        if get_bundle is None:
            return _error(400, "repository does not support get_client_bundle")
        try:
            return JSONResponse(get_bundle(client_id))
        except KeyError as exc:
            return _error(404, str(exc))

    @mcp.custom_route("/api/clients/{client_id}/sections/{section}", methods=["PATCH"])
    async def api_patch_client_section(request: Request) -> JSONResponse:
        """Patch one physical table section for a client (clients or satellite)."""
        client_id = _parse_row_id(request.path_params["client_id"])
        section = request.path_params["section"]
        if not isinstance(client_id, int):
            return _error(400, "client_id must be an integer")
        if section not in CLIENT_SECTIONS:
            return _error(
                400,
                f"Unknown section {section!r}. Expected one of: {list(CLIENT_SECTIONS)}",
            )
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return _error(400, "JSON body required")
        fields = body.get("fields") if isinstance(body, dict) else None
        if not isinstance(fields, dict):
            return _error(400, 'body must be {"fields": {...}}')
        # Never allow retargeting the FK / PK from the section editor.
        fields = {
            key: value
            for key, value in fields.items()
            if key not in {"id", "client_id"}
        }
        repo.ensure_ready()
        try:
            result = repo.update_row(section, client_id, fields)
        except KeyError as exc:
            return _error(404, str(exc))
        except ValueError as exc:
            return _error(400, str(exc))
        logger.info(
            "admin section update client_id=%s section=%s fields=%s",
            client_id,
            section,
            list(fields),
        )
        return JSONResponse(result.model_dump(mode="json"))

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
        filters: dict[str, Any] = {}
        if "client_id" in request.query_params:
            try:
                filters["client_id"] = int(request.query_params["client_id"])
            except ValueError:
                return _error(400, "client_id must be an integer")
        repo.ensure_ready()
        try:
            result = repo.list_rows(
                table,
                filters=filters or None,
                search=search,
                limit=limit,
                offset=offset,
            )
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
