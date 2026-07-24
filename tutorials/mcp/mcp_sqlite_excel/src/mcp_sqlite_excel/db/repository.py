"""Schema-aware CRUD operations against the Excel-seeded SQLite database."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from mcp_sqlite_excel.db.excel_loader import bootstrap_from_excel
from mcp_sqlite_excel.models import (
    BootstrapSummary,
    ColumnInfo,
    CountByResult,
    DatabaseSchemaDescription,
    DeleteRowResult,
    FieldMap,
    ListRowsResult,
    RowResult,
    SortSpec,
    TableSchema,
)
from mcp_sqlite_excel.settings import AppSettings, get_settings

_log = logging.getLogger(__name__)


class SqliteCrudRepository:
    """CRUD helper that discovers tables/columns from SQLite PRAGMA metadata."""

    def __init__(
        self,
        db_path: Path | None = None,
        excel_path: Path | None = None,
        *,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db_path = Path(db_path or self.settings.sqlite_path)
        self.excel_path = Path(excel_path or self.settings.excel_path)
        _log.debug(
            "SqliteCrudRepository init: excel_path=%s db_path=%s",
            self.excel_path.resolve(),
            self.db_path.resolve(),
        )

    @contextmanager
    def _connect(self, *, readonly: bool = False) -> Iterator[sqlite3.Connection]:
        if readonly:
            uri = f"file:{self.db_path.as_posix()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
        else:
            conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            if not readonly:
                conn.commit()
        except Exception:
            if not readonly:
                conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_ready(self) -> None:
        """Bootstrap from Excel when the database file is missing."""
        if self.db_path.is_file():
            _log.info(
                "Reusing existing SQLite DB %s (skip Excel bootstrap from %s)",
                self.db_path.resolve(),
                self.excel_path.resolve(),
            )
            return
        _log.info(
            "No SQLite DB at %s — bootstrapping from Excel %s",
            self.db_path.resolve(),
            self.excel_path.resolve(),
        )
        bootstrap_from_excel(
            self.excel_path,
            self.db_path,
            replace=True,
            settings=self.settings,
        )

    def reset_from_excel(self) -> BootstrapSummary:
        """Drop the SQLite file and recreate it from the Excel workbook."""
        return bootstrap_from_excel(
            self.excel_path,
            self.db_path,
            replace=True,
            settings=self.settings,
        )

    def list_tables(self) -> list[str]:
        with self._connect(readonly=True) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        return [r["name"] for r in rows]

    def get_table_schema(self, table: str) -> TableSchema:
        table_name = self._resolve_table(table)
        with self._connect(readonly=True) as conn:
            pragma_rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        if not pragma_rows:
            raise KeyError(f"Unknown table: {table!r}")

        columns: list[ColumnInfo] = []
        for row in pragma_rows:
            name = row["name"]
            pk = bool(row["pk"])
            # Only the synthetic Excel-bootstrap key is autoincrement. An Excel
            # column literally named "id" is a caller-supplied primary key.
            autoincrement = pk and name == "row_id"
            columns.append(
                ColumnInfo(
                    name=name,
                    sqlite_type=row["type"] or "TEXT",
                    nullable=not bool(row["notnull"]) and not pk,
                    primary_key=pk,
                    autoincrement=autoincrement,
                    source_header=None,
                )
            )
        return TableSchema(name=table_name, columns=columns)

    def describe_schema(self) -> DatabaseSchemaDescription:
        return DatabaseSchemaDescription(
            db_path=self.db_path,
            excel_path=self.excel_path,
            tables=[self.get_table_schema(name) for name in self.list_tables()],
        )

    def list_rows(
        self,
        table: str,
        *,
        filters: dict[str, Any] | FieldMap | None = None,
        search: str | None = None,
        search_fields: list[str] | None = None,
        sort: list[SortSpec] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ListRowsResult:
        schema = self.get_table_schema(table)
        raw_filters = filters.root if isinstance(filters, FieldMap) else (filters or {})
        normalized = self._normalize_field_keys(schema, raw_filters)

        clauses: list[str] = []
        filter_params: list[Any] = []
        for key, value in normalized.items():
            if value is None:
                clauses.append(f"{key} IS NULL")
            else:
                clauses.append(f"{key} = ?")
                filter_params.append(value)

        applied_search = (search or "").strip() or None
        applied_search_fields: list[str] = []
        if applied_search is not None:
            applied_search_fields = self._resolve_search_fields(schema, search_fields)
            like = f"%{self._escape_like(applied_search)}%"
            search_clause = " OR ".join(f"CAST({col} AS TEXT) LIKE ? ESCAPE '\\'" for col in applied_search_fields)
            clauses.append(f"({search_clause})")
            filter_params.extend([like] * len(applied_search_fields))

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        applied_sort = list(sort or [])
        order_by = self._build_order_by(schema, applied_sort)
        sql = f"SELECT * FROM {schema.name} {where} ORDER BY {order_by} LIMIT ? OFFSET ?"

        with self._connect(readonly=True) as conn:
            rows = conn.execute(sql, [*filter_params, limit, offset]).fetchall()
            count_sql = f"SELECT COUNT(*) AS n FROM {schema.name} {where}"
            total = conn.execute(count_sql, filter_params).fetchone()["n"]

        return ListRowsResult(
            table=schema.name,
            count=len(rows),
            total_matching=total,
            limit=limit,
            offset=offset,
            search=applied_search,
            search_fields=applied_search_fields,
            sort=applied_sort,
            rows=[dict(r) for r in rows],
        )

    def count_by(self, table: str, column: str = "status") -> CountByResult:
        """Return COUNT(*) grouped by a column (for KPI tiles)."""
        schema = self.get_table_schema(table)
        resolved = self._normalize_field_keys(schema, {column: None})
        col_name = next(iter(resolved))
        sql = (
            f"SELECT CAST({col_name} AS TEXT) AS bucket, COUNT(*) AS n "
            f"FROM {schema.name} GROUP BY {col_name} ORDER BY n DESC, bucket ASC"
        )
        with self._connect(readonly=True) as conn:
            rows = conn.execute(sql).fetchall()
            total = conn.execute(f"SELECT COUNT(*) AS n FROM {schema.name}").fetchone()["n"]
        counts: dict[str, int] = {}
        for row in rows:
            key = "(null)" if row["bucket"] is None else str(row["bucket"])
            counts[key] = int(row["n"])
        return CountByResult(table=schema.name, column=col_name, total=total, counts=counts)

    def get_row(self, table: str, row_id: int | str) -> RowResult:
        schema = self.get_table_schema(table)
        pk = schema.pk_column.name
        with self._connect(readonly=True) as conn:
            row = conn.execute(
                f"SELECT * FROM {schema.name} WHERE {pk} = ?",
                (row_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"No row in {schema.name!r} with {pk}={row_id!r}")
        return RowResult(table=schema.name, row=dict(row))

    def create_row(self, table: str, fields: dict[str, Any] | FieldMap) -> RowResult:
        schema = self.get_table_schema(table)
        raw = fields.root if isinstance(fields, FieldMap) else fields
        payload = self._validate_write_fields(schema, raw, partial=False)
        cols = list(payload.keys())
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO {schema.name} ({', '.join(cols)}) VALUES ({placeholders})"
        with self._connect() as conn:
            cur = conn.execute(sql, [payload[c] for c in cols])
            inserted_id = cur.lastrowid
            pk = schema.pk_column.name
            lookup = payload[pk] if pk in payload else inserted_id
            row = conn.execute(
                f"SELECT * FROM {schema.name} WHERE {pk} = ?",
                (lookup,),
            ).fetchone()
        return RowResult(
            table=schema.name,
            row=dict(row) if row else {pk: inserted_id},
        )

    def update_row(
        self,
        table: str,
        row_id: int | str,
        fields: dict[str, Any] | FieldMap,
    ) -> RowResult:
        schema = self.get_table_schema(table)
        raw = fields.root if isinstance(fields, FieldMap) else fields
        payload = self._validate_write_fields(schema, raw, partial=True)
        if not payload:
            raise ValueError("fields must include at least one updatable column")
        pk = schema.pk_column.name
        if pk in payload:
            raise ValueError(f"Cannot update primary key column {pk!r}")

        assignments = ", ".join(f"{col} = ?" for col in payload)
        sql = f"UPDATE {schema.name} SET {assignments} WHERE {pk} = ?"
        params = [*payload.values(), row_id]
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            if cur.rowcount == 0:
                raise KeyError(f"No row in {schema.name!r} with {pk}={row_id!r}")
            row = conn.execute(
                f"SELECT * FROM {schema.name} WHERE {pk} = ?",
                (row_id,),
            ).fetchone()
        return RowResult(table=schema.name, row=dict(row))

    def delete_row(self, table: str, row_id: int | str) -> DeleteRowResult:
        schema = self.get_table_schema(table)
        pk = schema.pk_column.name
        with self._connect() as conn:
            existing = conn.execute(
                f"SELECT * FROM {schema.name} WHERE {pk} = ?",
                (row_id,),
            ).fetchone()
            if existing is None:
                raise KeyError(f"No row in {schema.name!r} with {pk}={row_id!r}")
            conn.execute(f"DELETE FROM {schema.name} WHERE {pk} = ?", (row_id,))
        return DeleteRowResult(table=schema.name, deleted=dict(existing))

    def _resolve_table(self, table: str) -> str:
        available = self.list_tables()
        if table in available:
            return table
        lowered = {name.lower(): name for name in available}
        if table.lower() in lowered:
            return lowered[table.lower()]
        raise KeyError(f"Unknown table: {table!r}. Available: {available}")

    def _normalize_field_keys(self, schema: TableSchema, fields: dict[str, Any]) -> dict[str, Any]:
        by_lower = {c.name.lower(): c.name for c in schema.columns}
        normalized: dict[str, Any] = {}
        for key, value in fields.items():
            resolved = by_lower.get(str(key).lower())
            if resolved is None:
                raise ValueError(
                    f"Unknown column {key!r} for table {schema.name!r}. Known columns: {sorted(schema.column_names)}"
                )
            normalized[resolved] = value
        return normalized

    @staticmethod
    def _escape_like(value: str) -> str:
        """Escape LIKE wildcards so search is substring-literal."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _resolve_search_fields(self, schema: TableSchema, search_fields: list[str] | None) -> list[str]:
        """Resolve columns for substring search (default: client_name + client_ref)."""
        if search_fields:
            return list(self._normalize_field_keys(schema, {name: None for name in search_fields}))

        defaults = ["client_name", "client_ref"]
        by_lower = {c.name.lower(): c.name for c in schema.columns}
        resolved = [by_lower[name] for name in defaults if name in by_lower]
        if resolved:
            return resolved

        # Generic fallback: all non-autoincrement columns.
        fallback = [c.name for c in schema.columns if not c.autoincrement]
        if not fallback:
            raise ValueError(f"No searchable columns on table {schema.name!r}")
        return fallback

    def _build_order_by(self, schema: TableSchema, sort: list[SortSpec]) -> str:
        """Build a safe ORDER BY clause from validated column names."""
        if not sort:
            return f"{schema.pk_column.name} ASC"
        parts: list[str] = []
        for spec in sort:
            resolved = self._normalize_field_keys(schema, {spec.field: None})
            col = next(iter(resolved))
            direction = "DESC" if spec.dir.lower() == "desc" else "ASC"
            parts.append(f"{col} {direction}")
        pk = schema.pk_column.name
        if not any(p.startswith(f"{pk} ") for p in parts):
            parts.append(f"{pk} ASC")
        return ", ".join(parts)

    def _validate_write_fields(
        self,
        schema: TableSchema,
        fields: dict[str, Any],
        *,
        partial: bool,
    ) -> dict[str, Any]:
        if not isinstance(fields, dict):
            raise TypeError("fields must be an object/dict of column → value")

        normalized = self._normalize_field_keys(schema, fields)

        for name in list(normalized):
            col = schema.get_column(name)
            if col and col.autoincrement:
                raise ValueError(f"Column {name!r} is auto-generated and must not be set")

        if not partial:
            pk = schema.pk_column
            if not pk.autoincrement and pk.name not in normalized:
                raise ValueError(f"Missing required primary key field: {pk.name}")

        return normalized
