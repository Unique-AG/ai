"""FastMCP server exposing schema-driven CRUD over an Excel-seeded SQLite DB."""

from __future__ import annotations

import json
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
from mcp_sqlite_excel.models import (
    EscalateForm,
    EscalateUpdateResult,
    EscalationEmailNotice,
    FieldMap,
    ListRowsResult,
    ServerStatus,
    ToolError,
    parse_search_fields_arg,
    parse_sort_arg,
)
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
        # Streamable HTTP returns the session id as a response header
        # (mcp-session-id), which the client must echo back on every later
        # request. Response headers are invisible to browser JS unless
        # explicitly exposed — without this, a direct browser client (no
        # platform/SDK in between, e.g. a local dashboard preview) can
        # complete `initialize` but every following call 400s with "Missing
        # session ID" because `response.headers.get(...)` silently returns
        # null cross-origin.
        expose_headers=["mcp-session-id"],
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


_ESCALATE_FIELD_NAMES = frozenset({"status", "state"})
_ESCALATE_VALUES = frozenset({"escalate", "escalated"})
# Keys agents often put in ``fields`` that belong to the notify email, not the row.
_ESCALATE_META_KEYS = frozenset(
    {
        "note",
        "recipient_email",
        "recipient",
        "email",
        "to",
        "notify_email",
        "notify",
    }
)


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


def _is_escalate_update(fields: dict[str, Any]) -> bool:
    """True when the patch sets status/state to escalate or Escalated."""
    for key, value in fields.items():
        if key.casefold() not in _ESCALATE_FIELD_NAMES:
            continue
        if str(value).strip().casefold() in _ESCALATE_VALUES:
            return True
    return False


def _default_escalate_note(row: dict[str, Any]) -> str:
    """Build a pre-filled escalation note from the row context."""
    client = row.get("client_name") or row.get("client_ref") or "this client"
    issue = row.get("open_issue") or row.get("recommended_action")
    if issue:
        return (
            f"Please review the escalation for {client}. "
            f"Open issue: {issue}. "
            "Confirm next steps with Compliance "
            "(EDD refresh, formal case, or return to RM)."
        )
    return prompts.DEFAULT_ESCALATE_NOTE


def _escalate_form_model(
    *,
    default_note: str,
    default_recipient: str,
) -> type[EscalateForm]:
    """Pydantic form type with row-/agent-specific defaults for elicitation UI."""
    from pydantic import create_model

    return create_model(
        "EscalateFormPrefill",
        __base__=EscalateForm,
        recipient_email=(
            str,
            Field(
                default=default_recipient,
                description=("Email address of the person who should be notified about this escalation."),
                min_length=3,
                pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            ),
        ),
        note=(
            str,
            Field(
                default=default_note,
                description="Note to include in the escalation email.",
            ),
        ),
    )


async def _elicit_escalate_form(
    ctx: Context,
    *,
    message: str,
    default_note: str,
    default_recipient: str,
) -> EscalateForm | None:
    """Collect escalation confirmation + notify email via a form elicitation."""
    form_type = _escalate_form_model(
        default_note=default_note,
        default_recipient=default_recipient,
    )
    result = await ctx.elicit(message, response_type=form_type)
    if result.action != "accept" or result.data is None:
        return None
    # Normalize to EscalateForm (dynamic subclass is fine for validation).
    return EscalateForm.model_validate(result.data.model_dump())


def _send_escalation_email(
    *,
    table: str,
    row_id: int | str,
    row: dict[str, Any],
    form: EscalateForm,
) -> EscalationEmailNotice:
    """Demo mail sender: log the escalation notice (no real SMTP)."""
    client_label = row.get("client_name") or row.get("client_ref") or row_id
    subject = f"[Escalation] {table} / {client_label} (row {row_id})"
    note = form.note.strip() or prompts.DEFAULT_ESCALATE_NOTE
    body_lines = [
        f"To: {form.recipient_email}",
        f"Subject: {subject}",
        "",
        "Hello,",
        "",
        f"An account-review record was escalated in `{table}`.",
        f"Client / ref: {client_label}",
        f"Row id: {row_id}",
        f"New status: {row.get('status') or row.get('state')}",
        "",
        "Message from reviewer:",
        note,
        "",
        "Row snapshot:",
        json.dumps(row, indent=2, default=str),
        "",
        "Please acknowledge and update the case as needed.",
    ]
    logger.info("Escalation email (demo):\n%s", "\n".join(body_lines))
    return EscalationEmailNotice(
        to=form.recipient_email,
        note=note,
        subject=subject,
        sent=True,
    )


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
            description='Optional object of exact-match filters, e.g. {"status":"Escalated"}.',
        ),
    ] = None,
    search: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Optional substring search (SQLite LIKE; ASCII case-insensitive). "
                "Defaults to client_name + client_ref when those columns exist; "
                "otherwise all writable columns. Override columns with search_fields."
            ),
        ),
    ] = None,
    search_fields: Annotated[
        list[str] | str | None,
        Field(
            default=None,
            description='Optional columns for search, e.g. ["client_name","client_ref"].',
        ),
    ] = None,
    sort: Annotated[
        list[dict[str, Any]] | str | None,
        Field(
            default=None,
            description='Optional sort specs, e.g. [{"field":"due_date","dir":"asc"}].',
        ),
    ] = None,
    limit: Annotated[int, Field(default=100, ge=1, le=2000)] = 100,
    offset: Annotated[int, Field(default=0, ge=0)] = 0,
) -> ListRowsResult:
    """Return a typed result so the iframe path ``rows`` matches the output schema."""
    repo.ensure_ready()
    parsed = FieldMap.from_mcp_arg(filters, field_name="filters")
    parsed_sort = parse_sort_arg(sort, field_name="sort")
    parsed_search_fields = parse_search_fields_arg(search_fields, field_name="search_fields")
    return repo.list_rows(
        table,
        filters=parsed,
        search=search,
        search_fields=parsed_search_fields,
        sort=parsed_sort,
        limit=limit,
        offset=offset,
    )


@mcp.tool(
    name="count_by",
    title="Count by column",
    description=prompts.COUNT_BY_DESCRIPTION,
    meta={
        "unique.app/icon": "chart",
        "unique.app/system-prompt": prompts.COUNT_BY_DESCRIPTION,
    },
)
async def count_by(
    table: Annotated[str, Field(description="Table name from list_schema.")],
    column: Annotated[
        str,
        Field(
            default="status",
            description='Column to group by (default "status" for KPI tiles).',
        ),
    ] = "status",
) -> str:
    try:
        repo.ensure_ready()
        return _dump(repo.count_by(table, column=column))
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


def _split_escalate_meta(
    fields: dict[str, Any] | None,
) -> tuple[dict[str, Any], str | None, str | None]:
    """Split row patches from notify-email keys agents often put in ``fields``.

    Returns ``(row_fields, note, recipient_email)``. Meta keys are removed from
    the row patch so they are never validated as table columns.
    """
    row_fields: dict[str, Any] = {}
    note: str | None = None
    recipient: str | None = None
    for key, value in (fields or {}).items():
        folded = key.casefold()
        if folded not in _ESCALATE_META_KEYS:
            row_fields[key] = value
            continue
        text = str(value).strip() if value is not None else ""
        if not text:
            continue
        if folded == "note":
            note = text
        else:
            # recipient_email / recipient / email / to / notify_email / notify
            recipient = text
    return row_fields, note, recipient


def _escalate_fields(fields: dict[str, Any] | None) -> dict[str, Any]:
    """Merge optional patches and ensure status/state is an escalate value."""
    payload = dict(fields or {})
    if _is_escalate_update(payload):
        return payload
    # Prefer overwriting status; fall back to state if that was the only key used.
    if any(k.casefold() == "state" for k in payload) and not any(k.casefold() == "status" for k in payload):
        payload["state"] = "Escalated"
    else:
        payload["status"] = "Escalated"
    return payload


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
    """Patch a row immediately with no elicitation."""
    try:
        repo.ensure_ready()
        parsed = FieldMap.from_mcp_arg(fields, field_name="fields")
        return _dump(repo.update_row(table, row_id, parsed))
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool(
    name="escalate_row",
    title="Escalate row",
    description=prompts.ESCALATE_ROW_DESCRIPTION,
    meta={
        "unique.app/icon": "alert-triangle",
        "unique.app/system-prompt": prompts.ESCALATE_ROW_DESCRIPTION,
    },
)
async def escalate_row(
    table: Annotated[str, Field(description="Table name from list_schema.")],
    row_id: Annotated[int | str, Field(description="Primary key value (id or row_id).")],
    ctx: Context,
    fields: Annotated[
        dict[str, Any] | str | None,
        Field(
            default=None,
            description=(
                "Optional extra *table columns* to set with the escalation "
                '(e.g. {"recommended_action":"..."}). '
                'If status/state is omitted, status is set to "Escalated". '
                "Do not put note / recipient_email here — use those parameters "
                "(or they will be stripped from fields and used as email defaults)."
            ),
        ),
    ] = None,
    note: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Optional note for the escalation notify email (pre-fills the elicitation form). Not a database column."
            ),
        ),
    ] = None,
    recipient_email: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Optional Compliance recipient for the demo notify email "
                "(pre-fills the elicitation form). Not a database column."
            ),
        ),
    ] = None,
) -> str:
    """Confirm via form elicitation, then escalate and send the demo email."""
    try:
        repo.ensure_ready()
        parsed = FieldMap.from_mcp_arg(fields, field_name="fields")
        row_fields, fields_note, fields_recipient = _split_escalate_meta(parsed.root)
        payload = FieldMap(_escalate_fields(row_fields))
        existing = repo.get_row(table, row_id)
        default_note = (note or "").strip() or (fields_note or "").strip() or _default_escalate_note(existing.row)
        default_recipient = (
            (recipient_email or "").strip()
            or (fields_recipient or "").strip()
            or prompts.DEFAULT_ESCALATE_RECIPIENT_EMAIL
        )
        form = await _elicit_escalate_form(
            ctx,
            message=(
                f"{prompts.DEFAULT_ESCALATE_ELICIT_INTRO}\n\n"
                # f"Table: `{table}` · row {row_id!r}\n"
                # f"Default recipient: {default_recipient}\n\n"
                # f"Current row:\n{_dump(existing)}\n\n"
                # f"Requested change:\n{_dump(payload)}"
            ),
            default_note=default_note,
            default_recipient=default_recipient,
        )
        if form is None:
            return _dump(
                ToolError(
                    error="EscalateCancelled",
                    message=(f"Escalation of {table!r} row {row_id!r} was cancelled by the user."),
                )
            )
        updated = repo.update_row(table, row_id, payload)
        notice = _send_escalation_email(
            table=table,
            row_id=row_id,
            row=updated.row,
            form=form,
        )
        return _dump(
            EscalateUpdateResult(
                table=updated.table,
                row=updated.row,
                escalation_email=notice,
            )
        )
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
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )
    logging.getLogger("mcp_sqlite_excel").setLevel(logging.DEBUG)

    excel = Path(repo.excel_path).resolve()
    db = Path(repo.db_path).resolve()
    logger.info(
        "Dataset config: excel_path=%s exists=%s | sqlite_path=%s exists=%s | "
        "excel_header_row=%s excel_min_header_cells=%s",
        excel,
        excel.is_file(),
        db,
        db.is_file(),
        settings.excel_header_row,
        settings.excel_min_header_cells,
    )
    if db.is_file():
        logger.warning(
            "SQLite DB already exists at %s — Excel is NOT reloaded on startup. "
            "Delete the DB or call reset_from_excel to apply excel_path=%s",
            db,
            excel,
        )

    if not excel.is_file():
        from mcp_sqlite_excel.scripts.generate_sample_excel import generate

        logger.info("Excel missing; generating sample workbook at %s", excel)
        generate(excel)
    repo.ensure_ready()
    logger.info(
        "Ready: excel_path=%s db_path=%s tables=%s",
        Path(repo.excel_path).resolve(),
        Path(repo.db_path).resolve(),
        repo.list_tables() if Path(repo.db_path).is_file() else [],
    )

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
