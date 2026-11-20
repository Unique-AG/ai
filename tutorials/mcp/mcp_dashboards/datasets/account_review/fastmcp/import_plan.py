"""Excel import plan for the account_review dataset.

The generic framework loader still supports flat workbook imports. This dataset
uses a curated import plan instead: the Clients sheet is fanned out into
domain-aligned 1:1 SQLite tables plus normalized figure rows.
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


def _client_id_pk() -> ColumnInfo:
    return ColumnInfo(
        name="client_id",
        sqlite_type="INTEGER",
        nullable=False,
        primary_key=True,
        autoincrement=False,
    )


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
        _column("name", nullable=False),
        _column("reference", nullable=False),
        _column("crd_number", nullable=False),
        _column("type", nullable=False),
        _column("segment", nullable=False),
    ],
)

CONTACTS_SCHEMA = TableSchema(
    name="contacts",
    source_sheet="Clients",
    columns=[
        _client_id_pk(),
        _column("date_of_birth"),
        _column("occupation"),
        _column("marital_status"),
        _column("nationality"),
        _column("residence"),
        _column("domicile"),
        _column("incorporation"),
        _column("residential_address"),
        _column("email"),
        _column("phone"),
    ],
)

PORTFOLIOS_SCHEMA = TableSchema(
    name="portfolios",
    source_sheet="Clients",
    columns=[
        _client_id_pk(),
        _column("onboarded", nullable=False),
        _column("currency", nullable=False),
        _column("value", "REAL", nullable=False),
    ],
)

COMPLIANCE_SCHEMA = TableSchema(
    name="compliance",
    source_sheet="Clients",
    columns=[
        _client_id_pk(),
        _column("risk_level", nullable=False),
        _column("risk_profile", nullable=False),
        _column("risk_tolerance", nullable=False),
        _column("criticality", nullable=False),
        _column("pep", nullable=False),
        _column("adverse_media", nullable=False),
        _column("sanctions", nullable=False),
        _column("fatca_us_person", nullable=False),
        _column("verification_source", nullable=False),
        _column("documents_on_file", nullable=False),
        _column("mandate_type", nullable=False),
        _column("client_categorization", nullable=False),
        _column("category_required"),
        _column("category_review_status", nullable=False),
    ],
)

REVIEW_SCHEDULES_SCHEMA = TableSchema(
    name="review_schedules",
    source_sheet="Clients",
    columns=[
        _client_id_pk(),
        _column("last_reviewed", nullable=False),
        _column("next_review_due", nullable=False),
        _column("kyc_refresh_due", nullable=False),
    ],
)

SUITABILITY_SCHEMA = TableSchema(
    name="suitability",
    source_sheet="Clients",
    columns=[
        _client_id_pk(),
        _column("investment_horizon", nullable=False),
        _column("knowledge_experience", nullable=False),
        _column("last_suitability_test", nullable=False),
        _column("suitability_outcome", nullable=False),
    ],
)

CASE_ACTIONS_SCHEMA = TableSchema(
    name="case_actions",
    source_sheet="Clients",
    columns=[
        _client_id_pk(),
        _column("status", nullable=False),
        _column("rule_code"),
        _column("open_issue"),
        _column("recommended_action"),
        _column("due_date"),
        _column("title"),
        _column("explanation"),
        _column("button_label"),
        _column("button_target"),
        _column("owner"),
        _column("sof_transaction_amount", "REAL"),
        _column("sof_folder_id"),
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

# Parent + 1:1 satellites + figures. Order matches create/insert dependency.
ALL_SCHEMAS: tuple[TableSchema, ...] = (
    CLIENTS_SCHEMA,
    CONTACTS_SCHEMA,
    PORTFOLIOS_SCHEMA,
    COMPLIANCE_SCHEMA,
    REVIEW_SCHEDULES_SCHEMA,
    SUITABILITY_SCHEMA,
    CASE_ACTIONS_SCHEMA,
    FIGURE_METRICS_SCHEMA,
)

SATELLITE_SCHEMAS: tuple[TableSchema, ...] = (
    CONTACTS_SCHEMA,
    PORTFOLIOS_SCHEMA,
    COMPLIANCE_SCHEMA,
    REVIEW_SCHEDULES_SCHEMA,
    SUITABILITY_SCHEMA,
    CASE_ACTIONS_SCHEMA,
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


def _clients_row(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": source["client_name"],
        "reference": source["client_ref"],
        "crd_number": source["crd_number"],
        "type": source["type"],
        "segment": source["segment"],
    }


def _contacts_row(client_id: int, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "date_of_birth": source.get("date_of_birth"),
        "occupation": source.get("occupation"),
        "marital_status": source.get("marital_status"),
        "nationality": source.get("nationality"),
        "residence": source.get("residence"),
        "domicile": source.get("domicile"),
        "incorporation": source.get("incorporation"),
        "residential_address": source.get("residential_address"),
        "email": source.get("email"),
        "phone": source.get("phone"),
    }


def _portfolios_row(client_id: int, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "onboarded": source["onboarded"],
        "currency": source["currency"],
        "value": source["portfolio_value"],
    }


def _compliance_row(client_id: int, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "risk_level": source["risk_level"],
        "risk_profile": source["risk_profile"],
        "risk_tolerance": source["risk_tolerance"],
        "criticality": source["criticality"],
        "pep": source["pep"],
        "adverse_media": source["adverse_media"],
        "sanctions": source["sanctions"],
        "fatca_us_person": source["fatca_us_person"],
        "verification_source": source["verification_source"],
        "documents_on_file": source["documents_on_file"],
        "mandate_type": source["mandate_type"],
        "client_categorization": source["client_categorization"],
        "category_required": source.get("category_required"),
        "category_review_status": source["category_review_status"],
    }


def _review_schedules_row(client_id: int, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "last_reviewed": source["last_reviewed"],
        "next_review_due": source["next_review_due"],
        "kyc_refresh_due": source["kyc_refresh_due"],
    }


def _suitability_row(client_id: int, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "investment_horizon": source["investment_horizon"],
        "knowledge_experience": source["knowledge_experience"],
        "last_suitability_test": source["last_suitability_test"],
        "suitability_outcome": source["suitability_outcome"],
    }


def _case_actions_row(client_id: int, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "status": source["status"],
        "rule_code": source.get("rule_code"),
        "open_issue": source.get("open_issue"),
        "recommended_action": source.get("recommended_action"),
        "due_date": _normalize_due_date(source.get("due_date")),
        "title": source.get("action_title"),
        "explanation": source.get("action_explanation"),
        "button_label": source.get("action_button"),
        "button_target": source.get("action_button_target"),
        "owner": source.get("action_owner"),
        "sof_transaction_amount": source.get("sof_transaction_amount"),
        "sof_folder_id": source.get("sof_folder_id"),
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


def _fk_constraint(table: str = "clients") -> list[str]:
    return [f"FOREIGN KEY (client_id) REFERENCES {table}(id) ON DELETE CASCADE"]


def _insert_row(
    conn: sqlite3.Connection, schema: TableSchema, row: dict[str, Any]
) -> int | None:
    columns = [column.name for column in schema.writable_columns]
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {schema.name} ({', '.join(columns)}) VALUES ({placeholders})"
    cursor = conn.execute(sql, [row.get(column) for column in columns])
    return cursor.lastrowid


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
    figure_rows: list[dict[str, Any]] = []
    satellite_counts = {schema.name: 0 for schema in SATELLITE_SCHEMAS}
    try:
        with conn:
            conn.execute("PRAGMA foreign_keys = ON")
            create_table(conn, CLIENTS_SCHEMA)
            for schema in SATELLITE_SCHEMAS:
                create_table(conn, schema, table_constraints=_fk_constraint())
            create_table(
                conn,
                FIGURE_METRICS_SCHEMA,
                table_constraints=_fk_constraint(),
            )
            conn.execute(
                "CREATE INDEX idx_figure_metrics_client_id ON figure_metrics (client_id)"
            )

            # Insert one client at a time and read back the key SQLite actually
            # assigned, so satellite and figure rows attach to a real id.
            for source in source_rows:
                client_id = _insert_row(conn, CLIENTS_SCHEMA, _clients_row(source))
                if client_id is None:
                    raise RuntimeError(
                        f"SQLite assigned no id to client {source.get('client_ref')!r}"
                    )
                satellites = (
                    (CONTACTS_SCHEMA, _contacts_row(client_id, source)),
                    (PORTFOLIOS_SCHEMA, _portfolios_row(client_id, source)),
                    (COMPLIANCE_SCHEMA, _compliance_row(client_id, source)),
                    (REVIEW_SCHEDULES_SCHEMA, _review_schedules_row(client_id, source)),
                    (SUITABILITY_SCHEMA, _suitability_row(client_id, source)),
                    (CASE_ACTIONS_SCHEMA, _case_actions_row(client_id, source)),
                )
                for schema, row in satellites:
                    _insert_row(conn, schema, row)
                    satellite_counts[schema.name] += 1
                figure_rows.extend(_figure_rows(client_id, source))
            insert_rows(conn, FIGURE_METRICS_SCHEMA, figure_rows)
    finally:
        conn.close()

    table_summaries = [
        BootstrapTableSummary(
            table=CLIENTS_SCHEMA.name,
            source_sheet=CLIENTS_SCHEMA.source_sheet,
            columns=list(CLIENTS_SCHEMA.columns),
            row_count=len(source_rows),
        )
    ]
    for schema in SATELLITE_SCHEMAS:
        table_summaries.append(
            BootstrapTableSummary(
                table=schema.name,
                source_sheet=schema.source_sheet,
                columns=list(schema.columns),
                row_count=satellite_counts[schema.name],
            )
        )
    table_summaries.append(
        BootstrapTableSummary(
            table=FIGURE_METRICS_SCHEMA.name,
            source_sheet=FIGURE_METRICS_SCHEMA.source_sheet,
            columns=list(FIGURE_METRICS_SCHEMA.columns),
            row_count=len(figure_rows),
        )
    )
    return BootstrapSummary(
        excel_path=excel_path,
        db_path=db_path,
        tables=table_summaries,
    )
