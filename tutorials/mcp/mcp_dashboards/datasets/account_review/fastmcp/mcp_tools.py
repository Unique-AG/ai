"""MCP tool registrations for the account_review dataset."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

import paths as _paths  # noqa: F401
from constants import (
    ATTENTION_EXCLUDED_STATUSES,
    BREACH_STATUS,
    CountColumn,
    DEADLINE_STATUS,
    ESCALATION_STATUSES,
    MAX_PAGE_SIZE,
    SEARCH_COLUMNS,
    logger,
)
from domain import (
    apply_client_update,
    client_binding_rows,
    client_by_pk,
    clients_from_rows,
    filters_to_storage,
    sort_to_storage,
    storage_column,
)
from email_drafts import (
    apply_optional_status,
    default_email_draft,
    elicit_email_draft,
    email_str,
    normalize_audience,
    send_email_payload,
)
from generated.models import (
    Audience,
    Client,
    ClientEmailDraftResult,
    ClientFilter,
    ClientListResult,
    ClientUpdate,
    CountByResult,
    CountByRow,
    Status,
)
from generated.models import (
    SortSpec as DomainSortSpec,
)
from mcp_dashboards.elicitation import elicit_confirm
from mcp_dashboards.models import BootstrapSummary, DatabaseSchemaDescription
from mcp_dashboards.tools import tool_errors
from runtime import mcp, repo


@mcp.tool(
    name="list_clients",
    description="List account-review clients as nested domain objects.",
)
@tool_errors(logger)
def list_clients(
    filters: ClientFilter | None = None,
    search: str | None = None,
    sort: list[DomainSortSpec] | None = None,
    limit: Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE)] = 100,
    offset: Annotated[int, Field(ge=0)] = 0,
) -> ClientListResult:
    repo.ensure_ready()
    storage_filters, needs_attention = filters_to_storage(filters)
    if needs_attention:
        # Equality filters only in SQLite; exclude cleared / handed-off rows.
        result = repo.list_client_rows(
            filters=storage_filters,
            search=search,
            search_fields=SEARCH_COLUMNS,
            sort=sort_to_storage(sort),
            limit=MAX_PAGE_SIZE,
            offset=0,
        )
        attention_rows = [
            row
            for row in result.rows
            if row.get("case_action_status") not in ATTENTION_EXCLUDED_STATUSES
        ]
        total_matching = len(attention_rows)
        page = attention_rows[offset : offset + limit]
        clients = clients_from_rows(page)
        payload = ClientListResult(
            table="clients",
            count=len(clients),
            total_matching=total_matching,
            limit=limit,
            offset=offset,
            rows=clients,
        ).model_dump(mode="json")
        payload["rows"] = client_binding_rows(clients)
        return payload  # type: ignore[return-value]

    result = repo.list_client_rows(
        filters=storage_filters,
        search=search,
        search_fields=SEARCH_COLUMNS,
        sort=sort_to_storage(sort),
        limit=limit,
        offset=offset,
    )
    clients = clients_from_rows(result.rows)
    payload = ClientListResult(
        table="clients",
        count=result.count,
        total_matching=result.total_matching,
        limit=result.limit,
        offset=result.offset,
        rows=clients,
    ).model_dump(mode="json")
    payload["rows"] = client_binding_rows(clients)
    return payload  # type: ignore[return-value]


@mcp.tool(
    name="count_clients_by", description="Count clients by a supported domain field."
)
@tool_errors(logger)
def count_clients_by(column: CountColumn = "case_action.status") -> CountByResult:
    repo.ensure_ready()
    result = repo.count_clients_by(storage_column(column))
    # Built from `counts` rather than a generic count_by that prepends a
    # synthetic `__total__` bucket — that would render an extra "Total rows"
    # KPI tile the preview host never shows.
    return CountByResult(
        table="clients",
        column=column,
        total=result["total"],
        counts=dict(result["counts"]),
        rows=[
            CountByRow(bucket=bucket, label=bucket, count=count)
            for bucket, count in result["counts"].items()
        ],
    )


@mcp.tool(
    name="portfolio_kpis", description="Portfolio header KPI counts for the dashboard."
)
@tool_errors(logger)
def portfolio_kpis() -> CountByResult:
    repo.ensure_ready()
    rows = repo.list_client_rows(limit=MAX_PAGE_SIZE).rows
    total = len(rows)
    escalation = sum(
        1 for row in rows if row.get("case_action_status") in ESCALATION_STATUSES
    )
    breach = sum(1 for row in rows if row.get("case_action_status") == BREACH_STATUS)
    deadline = sum(
        1 for row in rows if row.get("case_action_status") == DEADLINE_STATUS
    )
    kpi_rows = [
        CountByRow(bucket="total", label="Total Clients", count=total),
        CountByRow(bucket="escalation", label="Escalation", count=escalation),
        CountByRow(bucket="breach", label="Breach", count=breach),
        CountByRow(bucket="deadline", label="Deadline approaching", count=deadline),
    ]
    return CountByResult(
        table="clients",
        column="portfolio",
        total=total,
        counts={row.bucket: row.count for row in kpi_rows},
        rows=kpi_rows,
    )


@mcp.tool(
    name="update_client",
    description=(
        "Patch client workflow fields. Status changes require user confirmation "
        "via MCP elicitation."
    ),
)
@tool_errors(logger)
async def update_client(
    pk: int, fields: ClientUpdate, ctx: Context | None = None
) -> Client:
    repo.ensure_ready()
    if fields.status is not None:
        if ctx is None:
            raise ToolError(
                "Status changes require an MCP client that supports elicitation."
            )
        client = client_by_pk(pk)
        new_status = (
            fields.status.value
            if isinstance(fields.status, Status)
            else str(fields.status)
        )
        confirmed = await elicit_confirm(
            ctx,
            f"Update status for **{client.identity.name}** "
            f"(`{client.identity.reference}`) from "
            f"**{client.case_action.status}** to **{new_status}**?",
        )
        if not confirmed:
            raise ToolError("Status update cancelled by user.")
    updated = apply_client_update(pk, fields)
    return client_binding_rows([updated])[0]  # type: ignore[return-value]


@mcp.tool(
    name="draft_client_email",
    description=(
        "Draft an email to the client or Compliance via MCP elicitation. "
        "Always pass signer_name as the currently logged-in user's display name "
        "(never invent a demo RM such as Elena Maltseva). "
        "The user reviews and edits to/subject/body/new_status; "
        "on accept the draft is returned and any status change is persisted. "
        "Nothing is sent — use send_email to deliver. "
        "Compliance mail goes to compliance@unique.ai."
    ),
)
@tool_errors(logger)
async def draft_client_email(
    pk: int,
    signer_name: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Display name of the currently logged-in user. Used as the email "
                "signature. Pass the real system user — do not invent a demo name."
            ),
        ),
    ],
    audience: Audience | str = Audience.client,
    ctx: Context | None = None,
) -> ClientEmailDraftResult:
    repo.ensure_ready()
    if ctx is None:
        raise ToolError(
            "draft_client_email requires an MCP client that supports elicitation."
        )
    resolved = normalize_audience(audience)
    client = client_by_pk(pk)
    draft = await elicit_email_draft(
        ctx=ctx,
        client=client,
        audience=resolved,
        send=False,
        signer_name=signer_name,
    )
    if draft is None:
        raise ToolError("Email draft cancelled by user.")
    client, status_updated = apply_optional_status(pk, client, draft.new_status)
    result = ClientEmailDraftResult(
        client=client, draft=draft, status_updated=status_updated
    )
    payload = result.model_dump(mode="json")
    payload["client"] = client_binding_rows([client])[0]
    return payload  # type: ignore[return-value]


@mcp.tool(
    name="send_email",
    description=(
        "Send an email to the client or Compliance. Always pass signer_name as the "
        "currently logged-in user's display name (never invent a demo RM such as "
        "Elena Maltseva). Elicits one editable draft form; accepting that form sends "
        "the email, while cancelling it sends nothing. Always returns whether the "
        "mail was sent (sent true/false + delivery_message) — even when the RM "
        "cancels, and even though delivery is a demo facade (no real SMTP; "
        "message_id is simulated). new_status is applied only when the edited form "
        "is accepted and the simulated send occurs. "
        "Compliance mail goes to compliance@unique.ai."
    ),
)
@tool_errors(logger)
async def send_email(
    pk: int,
    signer_name: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Display name of the currently logged-in user. Used as the email "
                "signature. Pass the real system user — do not invent a demo name."
            ),
        ),
    ],
    audience: Audience | str = Audience.client,
    ctx: Context | None = None,
) -> Any:
    repo.ensure_ready()
    if ctx is None:
        raise ToolError("send_email requires an MCP client that supports elicitation.")
    resolved = normalize_audience(audience)
    client = client_by_pk(pk)
    proposed = default_email_draft(client, resolved, signer_name=signer_name)
    draft = await elicit_email_draft(
        ctx=ctx,
        client=client,
        audience=resolved,
        send=True,
        signer_name=signer_name,
    )
    if draft is None:
        return send_email_payload(
            client=client,
            draft=proposed,
            sent=False,
            status_updated=False,
            message_id=None,
            delivery_message=(
                "Email not sent — draft review was cancelled by the user."
            ),
        )

    audience_label = "Compliance" if resolved is Audience.compliance else "the client"
    to_addr = email_str(draft.to)
    message_id = f"msg-{pk}-{resolved.value}-{uuid.uuid4().hex[:10]}"
    logger.info(
        "Simulated email send message_id=%s audience=%s subject=%s",
        message_id,
        resolved.value,
        draft.subject,
    )
    client, status_updated = apply_optional_status(pk, client, draft.new_status)
    return send_email_payload(
        client=client,
        draft=draft,
        sent=True,
        status_updated=status_updated,
        message_id=message_id,
        delivery_message=(
            f"Email sent to {to_addr} ({audience_label}) — simulated delivery "
            f"(facade; message_id={message_id})."
        ),
    )


@mcp.tool(
    name="list_schema",
    description="Return the live SQLite schema for the account_review dataset.",
)
@tool_errors(logger)
def list_schema() -> DatabaseSchemaDescription:
    repo.ensure_ready()
    return repo.describe_schema()


@mcp.tool(
    name="reset_from_excel",
    description="Reset the account_review SQLite database from its Excel workbook.",
)
@tool_errors(logger)
def reset_from_excel() -> BootstrapSummary:
    return repo.reset_from_excel()
