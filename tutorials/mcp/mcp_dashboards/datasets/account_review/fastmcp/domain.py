"""Domain ↔ storage mapping for account_review clients."""

from __future__ import annotations

from typing import Any

import paths as _paths  # noqa: F401
from constants import FILTER_ALIASES
from generated.models import (
    CaseAction,
    Client,
    ClientContact,
    ClientFilter,
    ClientIdentity,
    ClientUpdate,
    ComplianceProfile,
    DashboardFigures,
    Dir,
    FigureMetric,
    PortfolioSummary,
    ReviewSchedule,
    SuitabilityProfile,
)
from generated.models import (
    SortSpec as DomainSortSpec,
)
from import_plan import FIGURE_GROUPS
from mcp_dashboards.binding import enrich_binding_row
from mcp_dashboards.models import SortSpec
from runtime import repo


def storage_column(domain_path: str) -> str:
    """Map a domain path (or short filter alias) onto its storage column."""
    return FILTER_ALIASES.get(domain_path, domain_path).replace(".", "_")


def metric_from_row(row: dict[str, Any]) -> FigureMetric:
    return FigureMetric(
        label=row.get("label"),
        value=row.get("value"),
        pct=row.get("pct"),
        status=row.get("status"),
    )


def empty_figure_groups() -> dict[str, list[FigureMetric]]:
    return {group: [] for group in FIGURE_GROUPS}


def figures_by_client(client_ids: list[int]) -> dict[int, DashboardFigures]:
    """Load the figure rows for a whole page of clients in one query.

    Doing this per client made a 12-row `list_clients` open 41 SQLite
    connections; batching plus the repository's schema cache brings the same
    call down to two.
    """
    grouped: dict[int, dict[str, list[FigureMetric]]] = {
        client_id: empty_figure_groups() for client_id in client_ids
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
        groups[group_name].append(metric_from_row(row))
    return {
        client_id: DashboardFigures(**groups) for client_id, groups in grouped.items()
    }


def client_from_row(row: dict[str, Any], figures: DashboardFigures) -> Client:
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
            sof_transaction_amount=row.get("case_action_sof_transaction_amount"),
            sof_folder_id=row.get("case_action_sof_folder_id"),
        ),
        figures=figures,
    )


def clients_from_rows(rows: list[dict[str, Any]]) -> list[Client]:
    figures = figures_by_client([int(row["id"]) for row in rows])
    return [
        client_from_row(
            row, figures.get(int(row["id"]), DashboardFigures(**empty_figure_groups()))
        )
        for row in rows
    ]


def client_binding_rows(clients: list[Client]) -> list[dict[str, Any]]:
    """Nested domain rows plus flat dotted keys for the platform iframe host."""
    return [enrich_binding_row(client.model_dump(mode="json")) for client in clients]


def filters_to_storage(filters: ClientFilter | None) -> tuple[dict[str, Any], bool]:
    if filters is None:
        return {}, False
    data = filters.model_dump(exclude_none=True)
    needs_attention = bool(data.pop("needs_attention", False))
    return {
        storage_column(field): value for field, value in data.items()
    }, needs_attention


def sort_to_storage(sort: list[DomainSortSpec] | None) -> list[SortSpec]:
    return [
        SortSpec(
            field=storage_column(item.field),
            dir="desc" if item.dir is Dir.desc else "asc",
        )
        for item in sort or []
    ]


def update_to_storage(fields: ClientUpdate) -> dict[str, Any]:
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
            f"Add it to FILTER_ALIASES in constants.py alongside the TypeSpec change."
        )
    return {storage_column(field): value for field, value in patch.items()}


def client_by_pk(pk: int) -> Client:
    return clients_from_rows([repo.get_client_row(pk)])[0]


def apply_client_update(pk: int, fields: ClientUpdate) -> Client:
    row = repo.update_client_fields(pk, update_to_storage(fields))
    return clients_from_rows([row])[0]
