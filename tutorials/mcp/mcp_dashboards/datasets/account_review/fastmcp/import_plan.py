"""Excel import plan for the account_review dataset.

The generic framework loader still supports flat workbook imports. This dataset
uses a curated import plan instead: workbook columns are loaded into SQLite
columns that follow the TypeSpec domain model, plus normalized figure rows.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from mcp_dashboards.db.excel_loader import (
    create_table,
    insert_rows,
    read_excel_workbook,
)
from mcp_dashboards.models import (
    BootstrapSummary,
    BootstrapTableSummary,
    ColumnInfo,
    TableSchema,
)
from mcp_dashboards.settings import AppSettings


def _column(
    name: str, sqlite_type: str = "TEXT", *, nullable: bool = True
) -> ColumnInfo:
    return ColumnInfo(name=name, sqlite_type=sqlite_type, nullable=nullable)


CLIENTS_SCHEMA = TableSchema(
    name="clients",
    source_sheet="Clients",
    columns=[
        ColumnInfo(
            name="id",
            sqlite_type="INTEGER",
            nullable=False,
            primary_key=True,
            autoincrement=True,
        ),
        _column("identity_name", nullable=False),
        _column("identity_reference", nullable=False),
        _column("identity_crd_number", nullable=False),
        _column("identity_type", nullable=False),
        _column("identity_segment", nullable=False),
        _column("contact_date_of_birth"),
        _column("contact_occupation"),
        _column("contact_marital_status"),
        _column("contact_nationality"),
        _column("contact_residence"),
        _column("contact_domicile"),
        _column("contact_incorporation"),
        _column("contact_residential_address"),
        _column("contact_email"),
        _column("contact_phone"),
        _column("portfolio_onboarded", nullable=False),
        _column("portfolio_currency", nullable=False),
        _column("portfolio_value", "REAL", nullable=False),
        _column("compliance_risk_level", nullable=False),
        _column("compliance_risk_profile", nullable=False),
        _column("compliance_risk_tolerance", nullable=False),
        _column("compliance_criticality", nullable=False),
        _column("compliance_pep", nullable=False),
        _column("compliance_adverse_media", nullable=False),
        _column("compliance_sanctions", nullable=False),
        _column("compliance_fatca_us_person", nullable=False),
        _column("compliance_verification_source", nullable=False),
        _column("compliance_documents_on_file", nullable=False),
        _column("compliance_mandate_type", nullable=False),
        _column("compliance_client_categorization", nullable=False),
        _column("compliance_category_required"),
        _column("compliance_category_review_status", nullable=False),
        _column("review_schedule_last_reviewed", nullable=False),
        _column("review_schedule_next_review_due", nullable=False),
        _column("review_schedule_kyc_refresh_due", nullable=False),
        _column("suitability_investment_horizon", nullable=False),
        _column("suitability_knowledge_experience", nullable=False),
        _column("suitability_last_suitability_test", nullable=False),
        _column("suitability_suitability_outcome", nullable=False),
        _column("case_action_status", nullable=False),
        _column("case_action_rule_code"),
        _column("case_action_open_issue"),
        _column("case_action_recommended_action"),
        _column("case_action_due_date"),
        _column("case_action_title"),
        _column("case_action_explanation"),
        _column("case_action_button_label"),
        _column("case_action_button_target"),
        _column("case_action_owner"),
    ],
)

FIGURE_METRICS_SCHEMA = TableSchema(
    name="figure_metrics",
    source_sheet="Clients",
    columns=[
        ColumnInfo(
            name="id",
            sqlite_type="INTEGER",
            nullable=False,
            primary_key=True,
            autoincrement=True,
        ),
        _column("client_id", "INTEGER", nullable=False),
        _column("group_name", nullable=False),
        _column("position", "INTEGER", nullable=False),
        _column("label"),
        _column("value"),
        _column("pct", "REAL"),
        _column("status"),
    ],
)

FIGURE_GROUPS = {
    "documents": "fig",
    "performance": "perf",
    "mandate": "mand",
    "holdings": "hold",
}
FIGURE_POSITIONS = (1, 2, 3)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _normalize_due_date(value: Any) -> str | None:
    """Coerce workbook due dates to ISO 8601 full-date text."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text or text in {"—", "-"}:
        return None
    if not _ISO_DATE.fullmatch(text):
        raise ValueError(f"Unrecognized due_date value {text!r}; expected YYYY-MM-DD")
    return text


REQUIRED_SOURCE_COLUMNS = (
    "client_name",
    "client_ref",
    "crd_number",
    "type",
    "segment",
    "onboarded",
    "currency",
    "portfolio_value",
    "risk_level",
    "risk_profile",
    "risk_tolerance",
    "criticality",
    "pep",
    "adverse_media",
    "sanctions",
    "fatca_us_person",
    "verification_source",
    "documents_on_file",
    "mandate_type",
    "client_categorization",
    "category_review_status",
    "last_reviewed",
    "next_review_due",
    "kyc_refresh_due",
    "investment_horizon",
    "knowledge_experience",
    "last_suitability_test",
    "suitability_outcome",
    "status",
)


def _source_clients(
    excel_path: Path, settings: AppSettings | None
) -> list[dict[str, Any]]:
    sheets = read_excel_workbook(
        excel_path,
        header_row=settings.excel_header_row if settings else None,
        min_header_cells=settings.excel_min_header_cells if settings else 3,
    )
    for schema, rows in sheets:
        if schema.name != "clients":
            continue
        _require_source_columns(excel_path, schema)
        return rows
    available = ", ".join(schema.name for schema, _ in sheets)
    raise ValueError(
        f"No usable Clients sheet found in {excel_path}. Sheets read as: {available}"
    )


def _require_source_columns(excel_path: Path, schema: TableSchema) -> None:
    """Fail with every missing column at once, not one KeyError at a time."""
    missing = [
        name for name in REQUIRED_SOURCE_COLUMNS if name not in schema.column_names
    ]
    if not missing:
        return
    raise ValueError(
        f"Sheet {schema.source_sheet!r} in {excel_path} is missing "
        f"{len(missing)} required column(s): {', '.join(missing)}. "
        f"Found: {', '.join(sorted(schema.column_names))}"
    )


def _client_row(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "identity_name": source["client_name"],
        "identity_reference": source["client_ref"],
        "identity_crd_number": source["crd_number"],
        "identity_type": source["type"],
        "identity_segment": source["segment"],
        "contact_date_of_birth": source.get("date_of_birth"),
        "contact_occupation": source.get("occupation"),
        "contact_marital_status": source.get("marital_status"),
        "contact_nationality": source.get("nationality"),
        "contact_residence": source.get("residence"),
        "contact_domicile": source.get("domicile"),
        "contact_incorporation": source.get("incorporation"),
        "contact_residential_address": source.get("residential_address"),
        "contact_email": source.get("email"),
        "contact_phone": source.get("phone"),
        "portfolio_onboarded": source["onboarded"],
        "portfolio_currency": source["currency"],
        "portfolio_value": source["portfolio_value"],
        "compliance_risk_level": source["risk_level"],
        "compliance_risk_profile": source["risk_profile"],
        "compliance_risk_tolerance": source["risk_tolerance"],
        "compliance_criticality": source["criticality"],
        "compliance_pep": source["pep"],
        "compliance_adverse_media": source["adverse_media"],
        "compliance_sanctions": source["sanctions"],
        "compliance_fatca_us_person": source["fatca_us_person"],
        "compliance_verification_source": source["verification_source"],
        "compliance_documents_on_file": source["documents_on_file"],
        "compliance_mandate_type": source["mandate_type"],
        "compliance_client_categorization": source["client_categorization"],
        "compliance_category_required": source.get("category_required"),
        "compliance_category_review_status": source["category_review_status"],
        "review_schedule_last_reviewed": source["last_reviewed"],
        "review_schedule_next_review_due": source["next_review_due"],
        "review_schedule_kyc_refresh_due": source["kyc_refresh_due"],
        "suitability_investment_horizon": source["investment_horizon"],
        "suitability_knowledge_experience": source["knowledge_experience"],
        "suitability_last_suitability_test": source["last_suitability_test"],
        "suitability_suitability_outcome": source["suitability_outcome"],
        "case_action_status": source["status"],
        "case_action_rule_code": source.get("rule_code"),
        "case_action_open_issue": source.get("open_issue"),
        "case_action_recommended_action": source.get("recommended_action"),
        "case_action_due_date": _normalize_due_date(source.get("due_date")),
        "case_action_title": source.get("action_title"),
        "case_action_explanation": source.get("action_explanation"),
        "case_action_button_label": source.get("action_button"),
        "case_action_button_target": source.get("action_button_target"),
        "case_action_owner": source.get("action_owner"),
    }


def _figure_rows(client_id: int, source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group_name, prefix in FIGURE_GROUPS.items():
        for position in FIGURE_POSITIONS:
            key = f"{prefix}{position}"
            rows.append(
                {
                    "client_id": client_id,
                    "group_name": group_name,
                    "position": position,
                    "label": source.get(f"{key}_label"),
                    "value": source.get(f"{key}_value"),
                    "pct": source.get(f"{key}_pct"),
                    "status": source.get(f"{key}_status"),
                }
            )
    return rows


def bootstrap_account_review_from_excel(
    excel_path: Path,
    db_path: Path,
    *,
    replace: bool = True,
    settings: AppSettings | None = None,
) -> BootstrapSummary:
    """Create the TypeSpec-aligned account_review SQLite database from Excel."""
    source_rows = _source_clients(excel_path, settings)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if replace and db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        with conn:
            create_table(conn, CLIENTS_SCHEMA)
            create_table(
                conn,
                FIGURE_METRICS_SCHEMA,
                table_constraints=[
                    "FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE"
                ],
            )
            conn.execute(
                "CREATE INDEX idx_figure_metrics_client_id ON figure_metrics (client_id)"
            )

            # Insert one client at a time and read back the key SQLite actually
            # assigned, so figure rows attach to a real id rather than to a
            # position guessed from workbook order.
            figure_rows: list[dict[str, Any]] = []
            for source in source_rows:
                cursor = conn.execute(*_client_insert(_client_row(source)))
                client_id = cursor.lastrowid
                if client_id is None:
                    raise RuntimeError(
                        f"SQLite assigned no id to client {source.get('client_ref')!r}"
                    )
                figure_rows.extend(_figure_rows(client_id, source))
            insert_rows(conn, FIGURE_METRICS_SCHEMA, figure_rows)
    finally:
        conn.close()

    return BootstrapSummary(
        excel_path=excel_path,
        db_path=db_path,
        tables=[
            BootstrapTableSummary(
                table=CLIENTS_SCHEMA.name,
                source_sheet=CLIENTS_SCHEMA.source_sheet,
                columns=list(CLIENTS_SCHEMA.columns),
                row_count=len(source_rows),
            ),
            BootstrapTableSummary(
                table=FIGURE_METRICS_SCHEMA.name,
                source_sheet=FIGURE_METRICS_SCHEMA.source_sheet,
                columns=list(FIGURE_METRICS_SCHEMA.columns),
                row_count=len(figure_rows),
            ),
        ],
    )


def _client_insert(row: dict[str, Any]) -> tuple[str, list[Any]]:
    columns = [column.name for column in CLIENTS_SCHEMA.writable_columns]
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {CLIENTS_SCHEMA.name} ({', '.join(columns)}) VALUES ({placeholders})"
    return sql, [row.get(column) for column in columns]
