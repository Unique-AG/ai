"""SQLite repository for the account_review dataset."""

from __future__ import annotations

from typing import Any

import paths as _paths  # noqa: F401
from import_plan import ALL_SCHEMAS, bootstrap_account_review_from_excel
from mcp_dashboards.db.repository import SqliteCrudRepository
from mcp_dashboards.models import BootstrapSummary, ListRowsResult, SortSpec
from mcp_dashboards.settings import AppSettings

CLIENT_SECTION_TABLES: tuple[str, ...] = (
    "clients",
    "contacts",
    "portfolios",
    "compliance",
    "review_schedules",
    "suitability",
    "case_actions",
)

# JOIN projects the legacy flat aliases (`identity_name`, …) so domain mapping
# stays mechanical. Filter/sort/search keys use these aliases.
_CLIENT_SELECT = """
SELECT
  clients.id AS id,
  clients.name AS identity_name,
  clients.reference AS identity_reference,
  clients.crd_number AS identity_crd_number,
  clients.type AS identity_type,
  clients.segment AS identity_segment,
  contacts.date_of_birth AS contact_date_of_birth,
  contacts.occupation AS contact_occupation,
  contacts.marital_status AS contact_marital_status,
  contacts.nationality AS contact_nationality,
  contacts.residence AS contact_residence,
  contacts.domicile AS contact_domicile,
  contacts.incorporation AS contact_incorporation,
  contacts.residential_address AS contact_residential_address,
  contacts.email AS contact_email,
  contacts.phone AS contact_phone,
  portfolios.onboarded AS portfolio_onboarded,
  portfolios.currency AS portfolio_currency,
  portfolios.value AS portfolio_value,
  compliance.risk_level AS compliance_risk_level,
  compliance.risk_profile AS compliance_risk_profile,
  compliance.risk_tolerance AS compliance_risk_tolerance,
  compliance.criticality AS compliance_criticality,
  compliance.pep AS compliance_pep,
  compliance.adverse_media AS compliance_adverse_media,
  compliance.sanctions AS compliance_sanctions,
  compliance.fatca_us_person AS compliance_fatca_us_person,
  compliance.verification_source AS compliance_verification_source,
  compliance.documents_on_file AS compliance_documents_on_file,
  compliance.mandate_type AS compliance_mandate_type,
  compliance.client_categorization AS compliance_client_categorization,
  compliance.category_required AS compliance_category_required,
  compliance.category_review_status AS compliance_category_review_status,
  review_schedules.last_reviewed AS review_schedule_last_reviewed,
  review_schedules.next_review_due AS review_schedule_next_review_due,
  review_schedules.kyc_refresh_due AS review_schedule_kyc_refresh_due,
  suitability.investment_horizon AS suitability_investment_horizon,
  suitability.knowledge_experience AS suitability_knowledge_experience,
  suitability.last_suitability_test AS suitability_last_suitability_test,
  suitability.suitability_outcome AS suitability_suitability_outcome,
  case_actions.status AS case_action_status,
  case_actions.rule_code AS case_action_rule_code,
  case_actions.open_issue AS case_action_open_issue,
  case_actions.recommended_action AS case_action_recommended_action,
  case_actions.due_date AS case_action_due_date,
  case_actions.title AS case_action_title,
  case_actions.explanation AS case_action_explanation,
  case_actions.button_label AS case_action_button_label,
  case_actions.button_target AS case_action_button_target,
  case_actions.owner AS case_action_owner,
  case_actions.sof_transaction_amount AS case_action_sof_transaction_amount,
  case_actions.sof_folder_id AS case_action_sof_folder_id
FROM clients
JOIN contacts ON contacts.client_id = clients.id
JOIN portfolios ON portfolios.client_id = clients.id
JOIN compliance ON compliance.client_id = clients.id
JOIN review_schedules ON review_schedules.client_id = clients.id
JOIN suitability ON suitability.client_id = clients.id
JOIN case_actions ON case_actions.client_id = clients.id
"""

_CLIENT_FROM = """
FROM clients
JOIN contacts ON contacts.client_id = clients.id
JOIN portfolios ON portfolios.client_id = clients.id
JOIN compliance ON compliance.client_id = clients.id
JOIN review_schedules ON review_schedules.client_id = clients.id
JOIN suitability ON suitability.client_id = clients.id
JOIN case_actions ON case_actions.client_id = clients.id
"""

# Flat alias -> qualified SQL expression for WHERE / ORDER BY / GROUP BY.
FLAT_COLUMN_SQL: dict[str, str] = {
    "id": "clients.id",
    "identity_name": "clients.name",
    "identity_reference": "clients.reference",
    "identity_crd_number": "clients.crd_number",
    "identity_type": "clients.type",
    "identity_segment": "clients.segment",
    "contact_date_of_birth": "contacts.date_of_birth",
    "contact_occupation": "contacts.occupation",
    "contact_marital_status": "contacts.marital_status",
    "contact_nationality": "contacts.nationality",
    "contact_residence": "contacts.residence",
    "contact_domicile": "contacts.domicile",
    "contact_incorporation": "contacts.incorporation",
    "contact_residential_address": "contacts.residential_address",
    "contact_email": "contacts.email",
    "contact_phone": "contacts.phone",
    "portfolio_onboarded": "portfolios.onboarded",
    "portfolio_currency": "portfolios.currency",
    "portfolio_value": "portfolios.value",
    "compliance_risk_level": "compliance.risk_level",
    "compliance_risk_profile": "compliance.risk_profile",
    "compliance_risk_tolerance": "compliance.risk_tolerance",
    "compliance_criticality": "compliance.criticality",
    "compliance_pep": "compliance.pep",
    "compliance_adverse_media": "compliance.adverse_media",
    "compliance_sanctions": "compliance.sanctions",
    "compliance_fatca_us_person": "compliance.fatca_us_person",
    "compliance_verification_source": "compliance.verification_source",
    "compliance_documents_on_file": "compliance.documents_on_file",
    "compliance_mandate_type": "compliance.mandate_type",
    "compliance_client_categorization": "compliance.client_categorization",
    "compliance_category_required": "compliance.category_required",
    "compliance_category_review_status": "compliance.category_review_status",
    "review_schedule_last_reviewed": "review_schedules.last_reviewed",
    "review_schedule_next_review_due": "review_schedules.next_review_due",
    "review_schedule_kyc_refresh_due": "review_schedules.kyc_refresh_due",
    "suitability_investment_horizon": "suitability.investment_horizon",
    "suitability_knowledge_experience": "suitability.knowledge_experience",
    "suitability_last_suitability_test": "suitability.last_suitability_test",
    "suitability_suitability_outcome": "suitability.suitability_outcome",
    "case_action_status": "case_actions.status",
    "case_action_rule_code": "case_actions.rule_code",
    "case_action_open_issue": "case_actions.open_issue",
    "case_action_recommended_action": "case_actions.recommended_action",
    "case_action_due_date": "case_actions.due_date",
    "case_action_title": "case_actions.title",
    "case_action_explanation": "case_actions.explanation",
    "case_action_button_label": "case_actions.button_label",
    "case_action_button_target": "case_actions.button_target",
    "case_action_owner": "case_actions.owner",
    "case_action_sof_transaction_amount": "case_actions.sof_transaction_amount",
    "case_action_sof_folder_id": "case_actions.sof_folder_id",
}

# Flat alias -> (table, physical column) for routed PATCH updates.
FLAT_UPDATE_TARGET: dict[str, tuple[str, str]] = {
    "identity_name": ("clients", "name"),
    "identity_reference": ("clients", "reference"),
    "identity_crd_number": ("clients", "crd_number"),
    "identity_type": ("clients", "type"),
    "identity_segment": ("clients", "segment"),
    "contact_date_of_birth": ("contacts", "date_of_birth"),
    "contact_occupation": ("contacts", "occupation"),
    "contact_marital_status": ("contacts", "marital_status"),
    "contact_nationality": ("contacts", "nationality"),
    "contact_residence": ("contacts", "residence"),
    "contact_domicile": ("contacts", "domicile"),
    "contact_incorporation": ("contacts", "incorporation"),
    "contact_residential_address": ("contacts", "residential_address"),
    "contact_email": ("contacts", "email"),
    "contact_phone": ("contacts", "phone"),
    "portfolio_onboarded": ("portfolios", "onboarded"),
    "portfolio_currency": ("portfolios", "currency"),
    "portfolio_value": ("portfolios", "value"),
    "compliance_risk_level": ("compliance", "risk_level"),
    "compliance_risk_profile": ("compliance", "risk_profile"),
    "compliance_risk_tolerance": ("compliance", "risk_tolerance"),
    "compliance_criticality": ("compliance", "criticality"),
    "compliance_pep": ("compliance", "pep"),
    "compliance_adverse_media": ("compliance", "adverse_media"),
    "compliance_sanctions": ("compliance", "sanctions"),
    "compliance_fatca_us_person": ("compliance", "fatca_us_person"),
    "compliance_verification_source": ("compliance", "verification_source"),
    "compliance_documents_on_file": ("compliance", "documents_on_file"),
    "compliance_mandate_type": ("compliance", "mandate_type"),
    "compliance_client_categorization": ("compliance", "client_categorization"),
    "compliance_category_required": ("compliance", "category_required"),
    "compliance_category_review_status": ("compliance", "category_review_status"),
    "review_schedule_last_reviewed": ("review_schedules", "last_reviewed"),
    "review_schedule_next_review_due": ("review_schedules", "next_review_due"),
    "review_schedule_kyc_refresh_due": ("review_schedules", "kyc_refresh_due"),
    "suitability_investment_horizon": ("suitability", "investment_horizon"),
    "suitability_knowledge_experience": ("suitability", "knowledge_experience"),
    "suitability_last_suitability_test": ("suitability", "last_suitability_test"),
    "suitability_suitability_outcome": ("suitability", "suitability_outcome"),
    "case_action_status": ("case_actions", "status"),
    "case_action_rule_code": ("case_actions", "rule_code"),
    "case_action_open_issue": ("case_actions", "open_issue"),
    "case_action_recommended_action": ("case_actions", "recommended_action"),
    "case_action_due_date": ("case_actions", "due_date"),
    "case_action_title": ("case_actions", "title"),
    "case_action_explanation": ("case_actions", "explanation"),
    "case_action_button_label": ("case_actions", "button_label"),
    "case_action_button_target": ("case_actions", "button_target"),
    "case_action_owner": ("case_actions", "owner"),
    "case_action_sof_transaction_amount": ("case_actions", "sof_transaction_amount"),
    "case_action_sof_folder_id": ("case_actions", "sof_folder_id"),
}

_REQUIRED_TABLES = frozenset(schema.name for schema in ALL_SCHEMAS)


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
            tables = set(self.list_tables())
            if not _REQUIRED_TABLES.issubset(tables):
                return False
            clients = self.get_table_schema("clients")
            case_actions = self.get_table_schema("case_actions")
            compliance = self.get_table_schema("compliance")
        except Exception:  # noqa: BLE001 - any failure here means "rebuild it"
            return False
        return (
            {"name", "reference", "segment"}.issubset(clients.column_names)
            and "status" in case_actions.column_names
            and "risk_level" in compliance.column_names
        )

    def list_client_rows(
        self,
        *,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        search_fields: list[str] | None = None,
        sort: list[SortSpec] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ListRowsResult:
        """List joined client rows projected to flat domain aliases."""
        where_sql, params = self._client_where(
            filters=filters, search=search, search_fields=search_fields
        )
        applied_search = (search or "").strip() or None
        applied_search_fields = list(search_fields or []) if applied_search else []
        applied_sort = list(sort or [])
        order_by = self._client_order_by(applied_sort)
        sql = f"{_CLIENT_SELECT} {where_sql} ORDER BY {order_by} LIMIT ? OFFSET ?"
        count_sql = f"SELECT COUNT(*) AS n {_CLIENT_FROM} {where_sql}"
        with self._connect(readonly=True) as conn:
            rows = conn.execute(sql, [*params, limit, offset]).fetchall()
            total = conn.execute(count_sql, params).fetchone()["n"]
        return ListRowsResult(
            table="clients",
            count=len(rows),
            total_matching=int(total),
            limit=limit,
            offset=offset,
            search=applied_search,
            search_fields=applied_search_fields,
            sort=applied_sort,
            rows=[dict(row) for row in rows],
        )

    def get_client_row(self, pk: int) -> dict[str, Any]:
        sql = f"{_CLIENT_SELECT} WHERE clients.id = ?"
        with self._connect(readonly=True) as conn:
            row = conn.execute(sql, (pk,)).fetchone()
        if row is None:
            raise KeyError(f"No client with id={pk!r}")
        return dict(row)

    def get_client_bundle(self, pk: int) -> dict[str, Any]:
        """Load one client as editable physical table sections + figure rows."""
        sections: dict[str, dict[str, Any]] = {}
        for table in CLIENT_SECTION_TABLES:
            row_id = pk
            sections[table] = self.get_row(table, row_id).row
        figures = self.list_rows_where_in(
            "figure_metrics",
            column="client_id",
            values=[pk],
            sort=[SortSpec(field="group_name"), SortSpec(field="position")],
        )
        identity = sections["clients"]
        case_action = sections["case_actions"]
        return {
            "id": pk,
            "label": identity.get("name") or f"Client {pk}",
            "reference": identity.get("reference"),
            "status": case_action.get("status"),
            "sections": sections,
            "figure_metrics": figures,
        }

    def update_client_fields(self, pk: int, fields: dict[str, Any]) -> dict[str, Any]:
        """Route flat alias patches to the owning 1:1 table, then return joined row."""
        if not fields:
            raise ValueError("fields must include at least one updatable column")
        by_table: dict[str, dict[str, Any]] = {}
        for flat_key, value in fields.items():
            target = FLAT_UPDATE_TARGET.get(flat_key)
            if target is None:
                raise ValueError(
                    f"No storage table mapped for {flat_key!r}. "
                    f"Known flat columns: {sorted(FLAT_UPDATE_TARGET)}"
                )
            table, column = target
            by_table.setdefault(table, {})[column] = value

        with self._connect() as conn:
            for table, payload in by_table.items():
                assignments = ", ".join(f"{column} = ?" for column in payload)
                if table == "clients":
                    sql = f"UPDATE clients SET {assignments} WHERE id = ?"
                else:
                    sql = f"UPDATE {table} SET {assignments} WHERE client_id = ?"
                cursor = conn.execute(sql, [*payload.values(), pk])
                if cursor.rowcount == 0:
                    raise KeyError(f"No row in {table!r} for client id={pk!r}")

        return self.get_client_row(pk)

    def count_clients_by(self, column: str) -> dict[str, Any]:
        """Group joined clients by a flat alias column."""
        sql_column = self._resolve_flat_column(column)
        sql = (
            f"SELECT CAST({sql_column} AS TEXT) AS bucket, COUNT(*) AS n "
            f"{_CLIENT_FROM} GROUP BY {sql_column} ORDER BY n DESC, bucket ASC"
        )
        with self._connect(readonly=True) as conn:
            rows = conn.execute(sql).fetchall()
            total = conn.execute(f"SELECT COUNT(*) AS n {_CLIENT_FROM}").fetchone()["n"]
        counts = {
            ("(null)" if row["bucket"] is None else str(row["bucket"])): int(row["n"])
            for row in rows
        }
        return {"column": column, "total": int(total), "counts": counts}

    def _resolve_flat_column(self, field: str) -> str:
        resolved = FLAT_COLUMN_SQL.get(field)
        if resolved is None:
            # Allow already-qualified keys that match known values.
            if field in FLAT_COLUMN_SQL.values():
                return field
            raise ValueError(
                f"Unknown client column {field!r}. "
                f"Known: {sorted(FLAT_COLUMN_SQL)}"
            )
        return resolved

    def _client_where(
        self,
        *,
        filters: dict[str, Any] | None,
        search: str | None,
        search_fields: list[str] | None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for key, value in (filters or {}).items():
            sql_column = self._resolve_flat_column(key)
            if value is None:
                clauses.append(f"{sql_column} IS NULL")
            else:
                clauses.append(f"{sql_column} = ?")
                params.append(value)

        applied_search = (search or "").strip() or None
        if applied_search is not None:
            fields = search_fields or [
                "identity_name",
                "identity_reference",
                "case_action_open_issue",
                "case_action_recommended_action",
            ]
            like = f"%{self._escape_like(applied_search)}%"
            resolved = [self._resolve_flat_column(name) for name in fields]
            clauses.append(
                "("
                + " OR ".join(
                    f"CAST({column} AS TEXT) LIKE ? ESCAPE '\\'" for column in resolved
                )
                + ")"
            )
            params.extend([like] * len(resolved))

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, params

    def _client_order_by(self, sort: list[SortSpec]) -> str:
        if not sort:
            return "clients.id ASC"
        parts: list[str] = []
        for spec in sort:
            column = self._resolve_flat_column(spec.field)
            direction = "DESC" if spec.dir == "desc" else "ASC"
            parts.append(f"{column} {direction}")
        if not any(part.startswith("clients.id ") for part in parts):
            parts.append("clients.id ASC")
        return ", ".join(parts)
