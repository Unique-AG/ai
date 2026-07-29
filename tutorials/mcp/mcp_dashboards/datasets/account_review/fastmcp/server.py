"""Typed FastMCP app for the account_review dataset.

Tools are hand-written against the models generated from
`../contract/main.tsp` — there is no shared CRUD helper to inherit from. See
`docs/architecture.md` for why, and for the domain/storage mapping this file
owns.

Tools are declared `def`, not `async def`: every one of them does blocking
SQLite (and, for a reset, openpyxl) work, and FastMCP runs sync tools in a
worker thread instead of on the event loop.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

DATASET_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DATASET_ROOT.parents[2]
HELPER_SRC = PROJECT_ROOT / "helpers" / "python" / "src"
if str(DATASET_ROOT) not in sys.path:
    sys.path.insert(0, str(DATASET_ROOT))
if str(HELPER_SRC) not in sys.path:
    sys.path.insert(0, str(HELPER_SRC))

from generated.models import (  # noqa: E402
    CaseAction,
    Client,
    ClientContact,
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
    PortfolioSummary,
    ReviewSchedule,
    SuitabilityProfile,
)
from generated.models import (  # noqa: E402
    SortSpec as DomainSortSpec,
)
from import_plan import FIGURE_GROUPS, bootstrap_account_review_from_excel  # noqa: E402
from mcp_dashboards.binding import enrich_binding_row  # noqa: E402
from mcp_dashboards.db.repository import SqliteCrudRepository  # noqa: E402
from mcp_dashboards.models import (  # noqa: E402
    BootstrapSummary,
    DatabaseSchemaDescription,
    ServerStatus,
    SortSpec,
)
from mcp_dashboards.settings import AppSettings  # noqa: E402
from mcp_dashboards.tools import tool_errors  # noqa: E402

logger = logging.getLogger("account_review_mcp")

MAX_PAGE_SIZE = 500

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


settings = AppSettings(
    excel_path=DATASET_ROOT / "data" / "account_review_dataset.xlsx",
    sqlite_path=DATASET_ROOT / "data" / "account_review.sqlite",
)
repo = AccountReviewRepository(settings=settings)
mcp = FastMCP("Account Review Dashboard")

# Local-demo CORS: the live-local dashboard is served from a different origin
# (astro dev) than the MCP server, and there is no auth in front of either.
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


def _filters_to_storage(filters: ClientFilter | None) -> dict[str, Any]:
    if filters is None:
        return {}
    return {
        _storage_column(field): value
        for field, value in filters.model_dump(exclude_none=True).items()
    }


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
    result = repo.list_rows(
        "clients",
        filters=_filters_to_storage(filters),
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

    def _needs(row: dict[str, Any]) -> bool:
        return row.get("case_action_status") == "Needs Remediation"

    act_now = sum(
        1 for row in rows if _needs(row) and row.get("compliance_criticality") == "RED"
    )
    breach = sum(
        1
        for row in rows
        if _needs(row) and row.get("case_action_rule_code") == "R-SUIT-ALLOC"
    )
    watch = sum(
        1
        for row in rows
        if _needs(row) and row.get("compliance_criticality") == "AMBER"
    )
    kpi_rows = [
        CountByRow(bucket="total", label="Total Clients", count=total),
        CountByRow(bucket="act_now", label="Act now", count=act_now),
        CountByRow(bucket="breach", label="Breach", count=breach),
        CountByRow(bucket="watch", label="Watch", count=watch),
    ]
    return CountByResult(
        table="clients",
        column="portfolio",
        total=total,
        counts={row.bucket: row.count for row in kpi_rows},
        rows=kpi_rows,
    )


@mcp.tool(name="update_client", description="Patch client workflow fields.")
@tool_errors(logger)
def update_client(pk: int, fields: ClientUpdate) -> Client:
    repo.ensure_ready()
    result = repo.update_row("clients", pk, _update_to_storage(fields))
    return _client_binding_rows(_clients_from_rows([result.row]))[0]  # type: ignore[return-value]


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


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request) -> JSONResponse:  # noqa: ARG001
    tables: list[str] = []
    if repo.db_path.is_file():
        tables = repo.list_tables()
    status = ServerStatus(
        dataset="account_review",
        db_path=repo.db_path,
        excel_path=repo.excel_path,
        tables=tables,
    )
    return JSONResponse(status.model_dump(mode="json"))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    logger.info(
        "Starting account_review MCP with db=%s excel=%s", repo.db_path, repo.excel_path
    )
    repo.ensure_ready()
    mcp.run(
        transport="streamable-http",
        host=settings.host,
        port=settings.port,
        log_level="info",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
