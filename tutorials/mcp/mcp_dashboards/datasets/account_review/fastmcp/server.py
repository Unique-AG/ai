"""Typed FastMCP app for the account_review dataset.

Tools are hand-written against the models generated from
`../contract/main.tsp` — there is no shared CRUD helper to inherit from. See
`docs/architecture.md` for why, and for the domain/storage mapping this file
owns.

Tools that only touch SQLite are declared `def` so FastMCP runs them in a
worker thread. Tools that elicit (`update_client` status changes, `draft_client_email`,
`send_email`) are `async def` because they await MCP elicitation.
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, EmailStr, Field, create_model
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from unique_mcp.auth.zitadel.oidc_proxy import (
    ZitadelOIDCProxySettings,
    create_zitadel_oidc_proxy,
)
from unique_mcp.settings import ServerSettings

DATASET_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DATASET_ROOT.parents[2]
HELPER_SRC = PROJECT_ROOT / "helpers" / "python" / "src"
if str(DATASET_ROOT) not in sys.path:
    sys.path.insert(0, str(DATASET_ROOT))
# Monorepo layout only — in the Docker image mcp_dashboards is installed via uv.
if HELPER_SRC.is_dir() and str(HELPER_SRC) not in sys.path:
    sys.path.insert(0, str(HELPER_SRC))

from admin_site import register_admin_routes  # noqa: E402
from generated.models import (  # noqa: E402
    Audience,
    CaseAction,
    Client,
    ClientContact,
    ClientEmailDraftResult,
    ClientFilter,
    ClientIdentity,
    ClientListResult,
    ClientUpdate,
    ComplianceProfile,
    CountByResult,
    CountByRow,
    DashboardFigures,
    Dir,
    FigureMetric,
    OutboundEmailDraft,
    PortfolioSummary,
    ReviewSchedule,
    SendEmailResult,
    Status,
    SuitabilityProfile,
)
from generated.models import (  # noqa: E402
    SortSpec as DomainSortSpec,
)
from import_plan import FIGURE_GROUPS, bootstrap_account_review_from_excel  # noqa: E402
from mcp_dashboards.binding import enrich_binding_row  # noqa: E402
from mcp_dashboards.db.repository import SqliteCrudRepository  # noqa: E402
from mcp_dashboards.elicitation import elicit_confirm, elicit_form  # noqa: E402
from mcp_dashboards.models import (  # noqa: E402
    BootstrapSummary,
    DatabaseSchemaDescription,
    SortSpec,
)
from mcp_dashboards.settings import AppSettings  # noqa: E402
from mcp_dashboards.tools import tool_errors  # noqa: E402

logger = logging.getLogger("account_review_mcp")

MAX_PAGE_SIZE = 500

ESCALATION_STATUSES = {
    Status.Escalated.value,
    Status.Screening_hit.value,
    Status.Regulatory_breach.value,
    Status.Regulatory_change.value,
}
BREACH_STATUS = Status.Limit_exceeded.value
DEADLINE_STATUS = Status.Deadline_approaching.value
COMPLIANT_STATUS = Status.Compliant.value
ESCALATED_STATUS = Status.Escalated.value
# Attention rail: open work only — Compliant is cleared, Escalated is with Compliance.
ATTENTION_EXCLUDED_STATUSES = {COMPLIANT_STATUS, ESCALATED_STATUS}
# Compliance escalation inbox (demo send is simulated; no real SMTP).
COMPLIANCE_INBOX = "compliance@unique.ai"

# The curated SQLite schema is flat (`identity_name`), while the TypeSpec
# contract is nested (`identity.name`). Storage columns are therefore the
# domain path with dots replaced by underscores, and these four are the
# short filter/group aliases the dashboard sends.
FILTER_ALIASES: dict[str, str] = {
    "status": "case_action.status",
    "risk_level": "compliance.risk_level",
    "segment": "identity.segment",
    "criticality": "compliance.criticality",
}
CountColumn = Literal[
    "case_action.status",
    "compliance.risk_level",
    "compliance.criticality",
    "identity.segment",
    "identity.type",
    "compliance.mandate_type",
]
SEARCH_COLUMNS = [
    "identity_name",
    "identity_reference",
    "case_action_open_issue",
    "case_action_recommended_action",
]


def _storage_column(domain_path: str) -> str:
    """Map a domain path (or short filter alias) onto its storage column."""
    return FILTER_ALIASES.get(domain_path, domain_path).replace(".", "_")


class AccountReviewRepository(SqliteCrudRepository):
    """Repository using the account_review Excel import plan."""

    def __init__(self, *, settings: AppSettings) -> None:
        super().__init__(settings=settings)
        self._ready = False

    def ensure_ready(self) -> None:
        """Bootstrap once per process, then get out of the way.

        The previous version re-read the table schema on every tool call just to
        confirm three column names still existed.
        """
        if self._ready:
            return
        if not self.db_path.is_file() or not self._has_account_review_shape():
            bootstrap_account_review_from_excel(
                self.excel_path, self.db_path, replace=True, settings=self.settings
            )
            self.invalidate_schema_cache()
        self._ready = True

    def reset_from_excel(self) -> BootstrapSummary:
        summary = bootstrap_account_review_from_excel(
            self.excel_path, self.db_path, replace=True, settings=self.settings
        )
        self.invalidate_schema_cache()
        self._ready = True
        return summary

    def _has_account_review_shape(self) -> bool:
        try:
            schema = self.get_table_schema("clients")
        except Exception:  # noqa: BLE001 - any failure here means "rebuild it"
            return False
        return {
            "identity_name",
            "case_action_status",
            "compliance_risk_level",
        }.issubset(schema.column_names)


def _load_settings() -> AppSettings:
    """Dataset-local defaults, overridable by EXCEL_PATH / SQLITE_PATH / AUTH_DISABLED."""
    kwargs: dict[str, Any] = {}
    # Constructor kwargs beat env vars — only inject defaults when unset so Azure
    # can persist the DB at SQLITE_PATH=/home/data/account_review.sqlite.
    if "EXCEL_PATH" not in os.environ:
        kwargs["excel_path"] = DATASET_ROOT / "data" / "account_review_dataset.xlsx"
    if "SQLITE_PATH" not in os.environ:
        kwargs["sqlite_path"] = DATASET_ROOT / "data" / "account_review.sqlite"
    # Live-local and tests run without Zitadel. deploy.sh sets AUTH_DISABLED=false
    # when ZITADEL_* credentials are present.
    if "AUTH_DISABLED" not in os.environ:
        kwargs["auth_disabled"] = True
    return AppSettings(**kwargs)


settings = _load_settings()
server_settings = ServerSettings()
repo = AccountReviewRepository(settings=settings)


def _build_mcp(cfg: AppSettings) -> FastMCP:
    if cfg.auth_disabled:
        logger.warning("AUTH_DISABLED=true — Zitadel OIDC is off (local demos only)")
        return FastMCP("Account Review Dashboard")

    oidc_proxy = create_zitadel_oidc_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oidc_proxy_settings=ZitadelOIDCProxySettings(),  # type: ignore[call-arg]
    )
    return FastMCP("Account Review Dashboard", auth=oidc_proxy)


mcp = _build_mcp(settings)

# CORS for browser clients (live-local dashboard). Streamable HTTP returns the
# session id as a response header that the client must echo — expose it.
custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
]


def _bind_host_and_port() -> tuple[str, int]:
    """Prefer UNIQUE_MCP_LOCAL_BASE_URL; fall back to AppSettings host/port (8004)."""
    if os.environ.get("UNIQUE_MCP_LOCAL_BASE_URL"):
        parsed = urlparse(str(server_settings.local_base_url))
        return parsed.hostname or "127.0.0.1", parsed.port or settings.port
    return settings.host, settings.port


def _allowed_hosts() -> list[str]:
    """Hostnames FastMCP may accept in the Host header (public URL + bind host)."""
    hosts: list[str] = []
    for url in (server_settings.public_base_url, server_settings.local_base_url):
        if url is None:
            continue
        hostname = urlparse(str(url)).hostname
        if hostname and hostname not in hosts:
            hosts.append(hostname)
    if settings.host not in hosts and settings.host not in {"0.0.0.0", "127.0.0.1"}:
        hosts.append(settings.host)
    return hosts


def _metric_from_row(row: dict[str, Any]) -> FigureMetric:
    return FigureMetric(
        label=row.get("label"),
        value=row.get("value"),
        pct=row.get("pct"),
        status=row.get("status"),
    )


def _empty_figure_groups() -> dict[str, list[FigureMetric]]:
    return {group: [] for group in FIGURE_GROUPS}


def _figures_by_client(client_ids: list[int]) -> dict[int, DashboardFigures]:
    """Load the figure rows for a whole page of clients in one query.

    Doing this per client made a 12-row `list_clients` open 41 SQLite
    connections; batching plus the repository's schema cache brings the same
    call down to two.
    """
    grouped: dict[int, dict[str, list[FigureMetric]]] = {
        client_id: _empty_figure_groups() for client_id in client_ids
    }
    rows = repo.list_rows_where_in(
        "figure_metrics",
        column="client_id",
        values=client_ids,
        sort=[SortSpec(field="group_name"), SortSpec(field="position")],
    )
    for row in rows:
        groups = grouped.get(int(row["client_id"]))
        group_name = str(row.get("group_name"))
        if groups is None or group_name not in groups:
            continue
        groups[group_name].append(_metric_from_row(row))
    return {
        client_id: DashboardFigures(**groups) for client_id, groups in grouped.items()
    }


def _client_from_row(row: dict[str, Any], figures: DashboardFigures) -> Client:
    return Client(
        id=row["id"],
        identity=ClientIdentity(
            name=row["identity_name"],
            reference=row["identity_reference"],
            crd_number=row["identity_crd_number"],
            type=row["identity_type"],
            segment=row["identity_segment"],
        ),
        contact=ClientContact(
            date_of_birth=row.get("contact_date_of_birth"),
            occupation=row.get("contact_occupation"),
            marital_status=row.get("contact_marital_status"),
            nationality=row.get("contact_nationality"),
            residence=row.get("contact_residence"),
            domicile=row.get("contact_domicile"),
            incorporation=row.get("contact_incorporation"),
            residential_address=row.get("contact_residential_address"),
            email=row.get("contact_email"),
            phone=row.get("contact_phone"),
        ),
        portfolio=PortfolioSummary(
            onboarded=row["portfolio_onboarded"],
            currency=row["portfolio_currency"],
            value=row["portfolio_value"],
        ),
        compliance=ComplianceProfile(
            risk_level=row["compliance_risk_level"],
            risk_profile=row["compliance_risk_profile"],
            risk_tolerance=row["compliance_risk_tolerance"],
            criticality=row["compliance_criticality"],
            pep=row["compliance_pep"],
            adverse_media=row["compliance_adverse_media"],
            sanctions=row["compliance_sanctions"],
            fatca_us_person=row["compliance_fatca_us_person"],
            verification_source=row["compliance_verification_source"],
            documents_on_file=row["compliance_documents_on_file"],
            mandate_type=row["compliance_mandate_type"],
            client_categorization=row["compliance_client_categorization"],
            category_required=row.get("compliance_category_required"),
            category_review_status=row["compliance_category_review_status"],
        ),
        review_schedule=ReviewSchedule(
            last_reviewed=row["review_schedule_last_reviewed"],
            next_review_due=row["review_schedule_next_review_due"],
            kyc_refresh_due=row["review_schedule_kyc_refresh_due"],
        ),
        suitability=SuitabilityProfile(
            investment_horizon=row["suitability_investment_horizon"],
            knowledge_experience=row["suitability_knowledge_experience"],
            last_suitability_test=row["suitability_last_suitability_test"],
            suitability_outcome=row["suitability_suitability_outcome"],
        ),
        case_action=CaseAction(
            status=row["case_action_status"],
            rule_code=row.get("case_action_rule_code"),
            open_issue=row.get("case_action_open_issue"),
            recommended_action=row.get("case_action_recommended_action"),
            due_date=row.get("case_action_due_date"),
            title=row.get("case_action_title"),
            explanation=row.get("case_action_explanation"),
            button_label=row.get("case_action_button_label"),
            button_target=row.get("case_action_button_target"),
            owner=row.get("case_action_owner"),
        ),
        figures=figures,
    )


def _clients_from_rows(rows: list[dict[str, Any]]) -> list[Client]:
    figures = _figures_by_client([int(row["id"]) for row in rows])
    return [
        _client_from_row(
            row, figures.get(int(row["id"]), DashboardFigures(**_empty_figure_groups()))
        )
        for row in rows
    ]


def _client_binding_rows(clients: list[Client]) -> list[dict[str, Any]]:
    """Nested domain rows plus flat dotted keys for the platform iframe host."""
    return [enrich_binding_row(client.model_dump(mode="json")) for client in clients]


def _filters_to_storage(filters: ClientFilter | None) -> tuple[dict[str, Any], bool]:
    if filters is None:
        return {}, False
    data = filters.model_dump(exclude_none=True)
    needs_attention = bool(data.pop("needs_attention", False))
    return {
        _storage_column(field): value for field, value in data.items()
    }, needs_attention


def _sort_to_storage(sort: list[DomainSortSpec] | None) -> list[SortSpec]:
    return [
        SortSpec(
            field=_storage_column(item.field),
            dir="desc" if item.dir is Dir.desc else "asc",
        )
        for item in sort or []
    ]


def _update_to_storage(fields: ClientUpdate) -> dict[str, Any]:
    """Translate a patch, failing loudly on anything not mapped.

    A silent drop here used to mean that adding a field to `ClientUpdate` would
    make patches succeed while changing nothing.
    """
    patch = fields.model_dump(exclude_none=True)
    if not patch:
        raise ValueError(
            "fields must set at least one of: "
            + ", ".join(sorted(ClientUpdate.model_fields))
        )
    unknown = [field for field in patch if field not in FILTER_ALIASES]
    if unknown:
        raise ValueError(
            f"No storage column mapped for {', '.join(sorted(unknown))}. "
            f"Add it to FILTER_ALIASES in server.py alongside the TypeSpec change."
        )
    return {_storage_column(field): value for field, value in patch.items()}


def _client_by_pk(pk: int) -> Client:
    result = repo.get_row("clients", pk)
    return _clients_from_rows([result.row])[0]


def _apply_client_update(pk: int, fields: ClientUpdate) -> Client:
    result = repo.update_row("clients", pk, _update_to_storage(fields))
    return _clients_from_rows([result.row])[0]


def _email_str(value: Any) -> str:
    """Plain address text from an EmailAddress RootModel or raw string.

    ``str(EmailAddress(...))`` yields ``root='a@b.com'``, which breaks elicitation
    defaults and confirm copy — always unwrap via ``.root`` first.
    """
    if value is None:
        return ""
    root = getattr(value, "root", None)
    if root is not None:
        return str(root)
    return str(value)


def _normalize_signer_name(signer_name: str) -> str:
    name = signer_name.strip()
    if not name:
        raise ValueError(
            "signer_name is required — pass the logged-in user's display name."
        )
    return name


def _default_email_draft(
    client: Client,
    audience: Audience = Audience.client,
    *,
    signer_name: str,
) -> OutboundEmailDraft:
    signer = _normalize_signer_name(signer_name)
    issue = client.case_action.open_issue or "account review item"
    title = client.case_action.title or issue
    action = (
        client.case_action.recommended_action
        or "Please contact your relationship manager."
    )
    signature = f"Kind regards,\n{signer}"

    if audience is Audience.compliance:
        return OutboundEmailDraft(
            audience=Audience.compliance,
            to=COMPLIANCE_INBOX,
            subject=(
                f"Escalation: {client.identity.name} "
                f"({client.identity.reference}) — {title}"
            ),
            body=(
                f"Compliance team,\n\n"
                f"Please review the following client for escalation:\n\n"
                f"- Client: {client.identity.name} (`{client.identity.reference}`)\n"
                f"- Status: {client.case_action.status}\n"
                f"- Rule: {client.case_action.rule_code or '—'}\n"
                f"- Issue: {issue}\n"
                f"- Recommended action: {action}\n"
                f"- Criticality: {client.compliance.criticality}\n"
                f"- Risk: {client.compliance.risk_level}\n\n"
                f"{signature}"
            ),
            # Resolving a screening/regulatory hit by escalating → Escalated.
            new_status=Status.Escalated,
        )

    email = _email_str(client.contact.email)
    if not email:
        raise ValueError(
            f"Client {client.identity.name} has no contact email on file; "
            "cannot draft a client email."
        )
    return OutboundEmailDraft(
        audience=Audience.client,
        to=email,
        subject=f"Action required: {title}",
        body=(
            f"Dear {client.identity.name},\n\n"
            f"We are writing regarding {issue}.\n\n"
            f"{action}\n\n"
            f"{signature}"
        ),
    )


def _normalize_audience(audience: Audience | str | None) -> Audience:
    if audience is None:
        return Audience.client
    if isinstance(audience, Audience):
        return audience
    return Audience(str(audience))


def _email_draft_elicit_model(
    *,
    proposed: OutboundEmailDraft,
    client: Client,
    audience: Audience,
) -> type[BaseModel]:
    """Elicitation form for email drafts.

    Platform elicitation rejects nullable union types (``Status | None``), so
    ``new_status`` is a plain enum with a concrete default: Escalated for
    Compliance, otherwise the client's current status (accept = no change).
    """
    if proposed.new_status is not None:
        status_default = (
            proposed.new_status
            if isinstance(proposed.new_status, Status)
            else Status(str(proposed.new_status))
        )
    elif audience is Audience.compliance:
        status_default = Status.Escalated
    else:
        current = client.case_action.status
        status_default = (
            current if isinstance(current, Status) else Status(str(current))
        )

    return create_model(
        "EmailDraftForm",
        __base__=BaseModel,
        to=(
            EmailStr,
            Field(
                default=_email_str(proposed.to),
                description="Recipient email address.",
            ),
        ),
        subject=(
            str,
            Field(default=proposed.subject, description="Email subject line."),
        ),
        body=(
            str,
            Field(default=proposed.body, description="Email body text."),
        ),
        new_status=(
            Status,
            Field(
                default=status_default,
                description=(
                    "Workflow status to apply after accept. Keep the current status "
                    "for no change; Compliance escalations default to Escalated."
                ),
            ),
        ),
    )


async def _elicit_email_draft(
    *,
    ctx: Context,
    client: Client,
    audience: Audience,
    send: bool,
    signer_name: str,
) -> OutboundEmailDraft | None:
    """Elicit an email draft. Returns ``None`` when the user cancels review."""
    proposed = _default_email_draft(client, audience, signer_name=signer_name)
    audience_label = "Compliance" if audience is Audience.compliance else "the client"
    verb = "send" if send else "keep as a draft"
    EmailDraftForm = _email_draft_elicit_model(
        proposed=proposed, client=client, audience=audience
    )
    accepted = await elicit_form(
        ctx,
        f"Review the {audience.value} email for **{client.identity.name}** "
        f"(`{client.identity.reference}`) to {audience_label}. "
        f"Edit fields as needed, then accept to {verb}."
        + (
            " Sending to Compliance will set status to Escalated unless you change new_status."
            if audience is Audience.compliance
            else ""
        ),
        EmailDraftForm,
    )
    if accepted is None:
        return None
    return OutboundEmailDraft(
        audience=audience,
        to=_email_str(getattr(accepted, "to", None)) or _email_str(proposed.to),
        subject=getattr(accepted, "subject", None) or proposed.subject,
        body=getattr(accepted, "body", None) or proposed.body,
        new_status=accepted.new_status,
    )


def _send_email_payload(
    *,
    client: Client,
    draft: OutboundEmailDraft,
    sent: bool,
    status_updated: bool,
    message_id: str | None,
    delivery_message: str,
) -> dict[str, Any]:
    """Build the JSON tool result; always answers whether the mail was sent."""
    result = SendEmailResult(
        client=client,
        draft=draft,
        sent=sent,
        status_updated=status_updated,
        message_id=message_id,
        delivery_message=delivery_message,
    )
    payload = result.model_dump(mode="json")
    payload["client"] = _client_binding_rows([client])[0]
    return payload


def _apply_optional_status(
    pk: int, client: Client, new_status: Any
) -> tuple[Client, bool]:
    if new_status is None:
        return client, False
    status_value = (
        new_status if isinstance(new_status, Status) else Status(str(new_status))
    )
    if status_value == client.case_action.status:
        return client, False
    return _apply_client_update(pk, ClientUpdate(status=status_value)), True


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
    storage_filters, needs_attention = _filters_to_storage(filters)
    if needs_attention:
        # Equality filters only in SQLite; exclude cleared / handed-off rows.
        result = repo.list_rows(
            "clients",
            filters=storage_filters,
            search=search,
            search_fields=SEARCH_COLUMNS,
            sort=_sort_to_storage(sort),
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
        clients = _clients_from_rows(page)
        payload = ClientListResult(
            table="clients",
            count=len(clients),
            total_matching=total_matching,
            limit=limit,
            offset=offset,
            rows=clients,
        ).model_dump(mode="json")
        payload["rows"] = _client_binding_rows(clients)
        return payload  # type: ignore[return-value]

    result = repo.list_rows(
        "clients",
        filters=storage_filters,
        search=search,
        search_fields=SEARCH_COLUMNS,
        sort=_sort_to_storage(sort),
        limit=limit,
        offset=offset,
    )
    clients = _clients_from_rows(result.rows)
    payload = ClientListResult(
        table="clients",
        count=result.count,
        total_matching=result.total_matching,
        limit=result.limit,
        offset=result.offset,
        rows=clients,
    ).model_dump(mode="json")
    payload["rows"] = _client_binding_rows(clients)
    return payload  # type: ignore[return-value]


@mcp.tool(
    name="count_clients_by", description="Count clients by a supported domain field."
)
@tool_errors(logger)
def count_clients_by(column: CountColumn = "case_action.status") -> CountByResult:
    repo.ensure_ready()
    result = repo.count_by("clients", column=_storage_column(column))
    # Built from `counts` rather than the repository's own `rows`, which prepends
    # a synthetic `__total__` bucket. That bucket is a generic-tool convenience,
    # and letting it through would render an extra "Total rows" KPI tile that the
    # preview host — which derives buckets from the rows it has — never shows.
    return CountByResult(
        table="clients",
        column=column,
        total=result.total,
        counts=dict(result.counts),
        rows=[
            CountByRow(bucket=bucket, label=bucket, count=count)
            for bucket, count in result.counts.items()
        ],
    )


@mcp.tool(
    name="portfolio_kpis", description="Portfolio header KPI counts for the dashboard."
)
@tool_errors(logger)
def portfolio_kpis() -> CountByResult:
    repo.ensure_ready()
    rows = repo.list_rows("clients", limit=MAX_PAGE_SIZE).rows
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
        client = _client_by_pk(pk)
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
    updated = _apply_client_update(pk, fields)
    return _client_binding_rows([updated])[0]  # type: ignore[return-value]


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
    resolved = _normalize_audience(audience)
    client = _client_by_pk(pk)
    draft = await _elicit_email_draft(
        ctx=ctx,
        client=client,
        audience=resolved,
        send=False,
        signer_name=signer_name,
    )
    if draft is None:
        raise ToolError("Email draft cancelled by user.")
    client, status_updated = _apply_optional_status(pk, client, draft.new_status)
    result = ClientEmailDraftResult(
        client=client, draft=draft, status_updated=status_updated
    )
    payload = result.model_dump(mode="json")
    payload["client"] = _client_binding_rows([client])[0]
    return payload  # type: ignore[return-value]


@mcp.tool(
    name="send_email",
    description=(
        "Send an email to the client or Compliance. Always pass signer_name as the "
        "currently logged-in user's display name (never invent a demo RM such as "
        "Elena Maltseva). Elicits the draft for review and edit, then asks for an "
        "explicit send confirmation. Always returns whether the mail was sent "
        "(sent true/false + delivery_message) — even when the RM cancels, and even "
        "though delivery is a demo facade (no real SMTP; message_id is simulated). "
        "new_status is applied only on a confirmed send. "
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
) -> SendEmailResult:
    repo.ensure_ready()
    if ctx is None:
        raise ToolError("send_email requires an MCP client that supports elicitation.")
    resolved = _normalize_audience(audience)
    client = _client_by_pk(pk)
    proposed = _default_email_draft(client, resolved, signer_name=signer_name)
    draft = await _elicit_email_draft(
        ctx=ctx,
        client=client,
        audience=resolved,
        send=True,
        signer_name=signer_name,
    )
    if draft is None:
        return _send_email_payload(  # type: ignore[return-value]
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
    to_addr = _email_str(draft.to)
    confirmed = await elicit_confirm(
        ctx,
        f"Send this email to **{to_addr}** ({audience_label}) for "
        f"**{client.identity.name}** (`{client.identity.reference}`)?\n\n"
        f"**Subject:** {draft.subject}",
    )
    if not confirmed:
        return _send_email_payload(  # type: ignore[return-value]
            client=client,
            draft=draft,
            sent=False,
            status_updated=False,
            message_id=None,
            delivery_message=(
                f"Email not sent — send confirmation was cancelled. "
                f"No message was delivered to {to_addr}."
            ),
        )

    message_id = f"msg-{pk}-{resolved.value}-{uuid.uuid4().hex[:10]}"
    logger.info(
        "Simulated email send message_id=%s audience=%s to=%s subject=%s",
        message_id,
        resolved.value,
        to_addr,
        draft.subject,
    )
    client, status_updated = _apply_optional_status(pk, client, draft.new_status)
    return _send_email_payload(  # type: ignore[return-value]
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


register_admin_routes(mcp, repo=repo, settings=settings, dataset="account_review")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    host, port = _bind_host_and_port()
    logger.info(
        "Starting account_review MCP with db=%s excel=%s host=%s port=%s",
        repo.db_path,
        repo.excel_path,
        host,
        port,
    )
    repo.ensure_ready()
    mcp.run(
        transport=server_settings.transport_scheme,
        host=host,
        port=port,
        log_level="info",
        middleware=custom_middleware,
        allowed_hosts=_allowed_hosts(),
    )


if __name__ == "__main__":
    main()
