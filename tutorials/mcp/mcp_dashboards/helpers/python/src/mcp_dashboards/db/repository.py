"""Schema-aware CRUD operations against one dataset's SQLite database."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from mcp_dashboards.db.excel_loader import bootstrap_from_excel
from mcp_dashboards.models import (
    BootstrapSummary,
    ColumnInfo,
    CountByResult,
    DatabaseSchemaDescription,
    DeleteRowResult,
    ListRowsResult,
    RowResult,
    SortSpec,
    TableSchema,
)
from mcp_dashboards.settings import AppSettings

_log = logging.getLogger(__name__)


class SqliteCrudRepository:
    """CRUD helper for a single Excel-seeded SQLite database."""

    def __init__(self, *, settings: AppSettings) -> None:
        self.settings = settings
        self.db_path = Path(settings.sqlite_path)
        self.excel_path = Path(settings.excel_path)
        self._schema_cache: dict[str, TableSchema] = {}
        self._table_names: list[str] | None = None
        _log.debug(
            "Repository init: excel_path=%s db_path=%s",
            self.excel_path.resolve(),
            self.db_path.resolve(),
        )

    def invalidate_schema_cache(self) -> None:
        """Forget cached table names and schemas.

        The schema is fixed once a dataset is bootstrapped, so it is cached and
        every reader reuses it. Anything that recreates tables must call this.
        """
        self._schema_cache.clear()
        self._table_names = None

    @contextmanager
    def _connect(self, *, readonly: bool = False) -> Iterator[sqlite3.Connection]:
        if readonly:
            uri = f"file:{self.db_path.as_posix()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
        else:
            conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Off by default in SQLite, so any FK a dataset declares is inert
        # unless every writing connection turns it on.
        conn.execute("PRAGMA foreign_keys = ON")
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
        """Bootstrap from this dataset's Excel file when the DB is missing."""
        if self.db_path.is_file():
            return
        bootstrap_from_excel(
            self.excel_path, self.db_path, replace=True, settings=self.settings
        )
        self.invalidate_schema_cache()

    def reset_from_excel(self) -> BootstrapSummary:
        """Drop this dataset's SQLite file and recreate it from Excel."""
        summary = bootstrap_from_excel(
            self.excel_path, self.db_path, replace=True, settings=self.settings
        )
        self.invalidate_schema_cache()
        return summary

    def list_tables(self) -> list[str]:
        if self._table_names is None:
            with self._connect(readonly=True) as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            self._table_names = [row["name"] for row in rows]
        return list(self._table_names)

    def get_table_schema(self, table: str) -> TableSchema:
        cached = self._schema_cache.get(table)
        if cached is not None:
            return cached
        table_name = self._resolve_table(table)
        with self._connect(readonly=True) as conn:
            rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        if not rows:
            raise KeyError(f"Unknown table: {table!r}")
        columns: list[ColumnInfo] = []
        for row in rows:
            name = row["name"]
            pk = bool(row["pk"])
            columns.append(
                ColumnInfo(
                    name=name,
                    sqlite_type=row["type"] or "TEXT",
                    nullable=not bool(row["notnull"]) and not pk,
                    primary_key=pk,
                    autoincrement=pk and name == "row_id",
                    source_header=None,
                )
            )
        schema = TableSchema(name=table_name, columns=columns)
        self._schema_cache[table] = schema
        self._schema_cache[table_name] = schema
        return schema

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
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        search_fields: list[str] | None = None,
        sort: list[SortSpec] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ListRowsResult:
        schema = self.get_table_schema(table)
        normalized = self._normalize_field_keys(schema, filters or {})
        clauses: list[str] = []
        params: list[Any] = []
        for key, value in normalized.items():
            if value is None:
                clauses.append(f"{key} IS NULL")
            else:
                clauses.append(f"{key} = ?")
                params.append(value)

        applied_search = (search or "").strip() or None
        applied_search_fields: list[str] = []
        if applied_search is not None:
            applied_search_fields = self._resolve_search_fields(schema, search_fields)
            like = f"%{self._escape_like(applied_search)}%"
            clauses.append(
                "("
                + " OR ".join(
                    f"CAST({column} AS TEXT) LIKE ? ESCAPE '\\'"
                    for column in applied_search_fields
                )
                + ")"
            )
            params.extend([like] * len(applied_search_fields))

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        applied_sort = list(sort or [])
        order_by = self._build_order_by(schema, applied_sort)
        sql = (
            f"SELECT * FROM {schema.name} {where} ORDER BY {order_by} LIMIT ? OFFSET ?"
        )
        with self._connect(readonly=True) as conn:
            rows = conn.execute(sql, [*params, limit, offset]).fetchall()
            total = conn.execute(
                f"SELECT COUNT(*) AS n FROM {schema.name} {where}", params
            ).fetchone()["n"]
        return ListRowsResult(
            table=schema.name,
            count=len(rows),
            total_matching=total,
            limit=limit,
            offset=offset,
            search=applied_search,
            search_fields=applied_search_fields,
            sort=applied_sort,
            rows=[dict(row) for row in rows],
        )

    def list_rows_where_in(
        self,
        table: str,
        *,
        column: str,
        values: Sequence[Any],
        sort: list[SortSpec] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch every row whose `column` matches one of `values`, in one query.

        Lets a caller load all children for a page of parents without issuing
        one query per parent. `column` and any sort fields are resolved against
        the live schema, same as every other identifier here.
        """
        schema = self.get_table_schema(table)
        if not values:
            return []
        column_name = next(iter(self._normalize_field_keys(schema, {column: None})))
        placeholders = ", ".join("?" for _ in values)
        order_by = self._build_order_by(schema, list(sort or []))
        sql = f"SELECT * FROM {schema.name} WHERE {column_name} IN ({placeholders}) ORDER BY {order_by}"
        with self._connect(readonly=True) as conn:
            rows = conn.execute(sql, list(values)).fetchall()
        return [dict(row) for row in rows]

    def count_by(self, table: str, column: str) -> CountByResult:
        schema = self.get_table_schema(table)
        resolved = self._normalize_field_keys(schema, {column: None})
        column_name = next(iter(resolved))
        sql = (
            f"SELECT CAST({column_name} AS TEXT) AS bucket, COUNT(*) AS n "
            f"FROM {schema.name} GROUP BY {column_name} ORDER BY n DESC, bucket ASC"
        )
        with self._connect(readonly=True) as conn:
            rows = conn.execute(sql).fetchall()
            total = conn.execute(f"SELECT COUNT(*) AS n FROM {schema.name}").fetchone()[
                "n"
            ]
        counts = {
            ("(null)" if row["bucket"] is None else str(row["bucket"])): int(row["n"])
            for row in rows
        }
        return CountByResult(
            table=schema.name, column=column_name, total=total, counts=counts
        )

    def get_row(self, table: str, row_id: int | str) -> RowResult:
        schema = self.get_table_schema(table)
        pk = schema.pk_column.name
        with self._connect(readonly=True) as conn:
            row = conn.execute(
                f"SELECT * FROM {schema.name} WHERE {pk} = ?", (row_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"No row in {schema.name!r} with {pk}={row_id!r}")
        return RowResult(table=schema.name, row=dict(row))

    def create_row(self, table: str, fields: dict[str, Any]) -> RowResult:
        schema = self.get_table_schema(table)
        payload = self._validate_write_fields(schema, fields, partial=False)
        columns = list(payload)
        placeholders = ", ".join("?" for _ in columns)
        sql = (
            f"INSERT INTO {schema.name} ({', '.join(columns)}) VALUES ({placeholders})"
        )
        with self._connect() as conn:
            cursor = conn.execute(sql, [payload[column] for column in columns])
            inserted_id = cursor.lastrowid
            pk = schema.pk_column.name
            lookup = payload[pk] if pk in payload else inserted_id
            row = conn.execute(
                f"SELECT * FROM {schema.name} WHERE {pk} = ?", (lookup,)
            ).fetchone()
        return RowResult(table=schema.name, row=dict(row) if row else {pk: inserted_id})

    def update_row(
        self, table: str, row_id: int | str, fields: dict[str, Any]
    ) -> RowResult:
        schema = self.get_table_schema(table)
        payload = self._validate_write_fields(schema, fields, partial=True)
        if not payload:
            raise ValueError("fields must include at least one updatable column")
        pk = schema.pk_column.name
        if pk in payload:
            raise ValueError(f"Cannot update primary key column {pk!r}")
        assignments = ", ".join(f"{column} = ?" for column in payload)
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE {schema.name} SET {assignments} WHERE {pk} = ?",
                [*payload.values(), row_id],
            )
            if cursor.rowcount == 0:
                raise KeyError(f"No row in {schema.name!r} with {pk}={row_id!r}")
            row = conn.execute(
                f"SELECT * FROM {schema.name} WHERE {pk} = ?", (row_id,)
            ).fetchone()
        return RowResult(table=schema.name, row=dict(row))

    def delete_row(self, table: str, row_id: int | str) -> DeleteRowResult:
        schema = self.get_table_schema(table)
        pk = schema.pk_column.name
        with self._connect() as conn:
            existing = conn.execute(
                f"SELECT * FROM {schema.name} WHERE {pk} = ?", (row_id,)
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

    def _normalize_field_keys(
        self, schema: TableSchema, fields: dict[str, Any]
    ) -> dict[str, Any]:
        by_lower = {column.name.lower(): column.name for column in schema.columns}
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
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _resolve_search_fields(
        self, schema: TableSchema, search_fields: list[str] | None
    ) -> list[str]:
        """Resolve the columns a free-text search runs against.

        Callers are expected to pass `search_fields`; searching every column is
        only a fallback so a generic tool still works on an unknown table.
        """
        if search_fields:
            return list(
                self._normalize_field_keys(
                    schema, {name: None for name in search_fields}
                )
            )
        fallback = [
            column.name for column in schema.columns if not column.autoincrement
        ]
        if not fallback:
            raise ValueError(f"No searchable columns on table {schema.name!r}")
        return fallback

    def _build_order_by(self, schema: TableSchema, sort: list[SortSpec]) -> str:
        if not sort:
            return f"{schema.pk_column.name} ASC"
        parts: list[str] = []
        for spec in sort:
            resolved = self._normalize_field_keys(schema, {spec.field: None})
            column = next(iter(resolved))
            direction = "DESC" if spec.dir == "desc" else "ASC"
            parts.append(f"{column} {direction}")
        pk = schema.pk_column.name
        if not any(part.startswith(f"{pk} ") for part in parts):
            parts.append(f"{pk} ASC")
        return ", ".join(parts)

    def _validate_write_fields(
        self, schema: TableSchema, fields: dict[str, Any], *, partial: bool
    ) -> dict[str, Any]:
        if not isinstance(fields, dict):
            raise TypeError("fields must be an object/dict of column to value")
        normalized = self._normalize_field_keys(schema, fields)
        for name in list(normalized):
            column = schema.get_column(name)
            if column and column.autoincrement:
                raise ValueError(
                    f"Column {name!r} is auto-generated and must not be set"
                )
        if not partial:
            pk = schema.pk_column
            if not pk.autoincrement and pk.name not in normalized:
                raise ValueError(f"Missing required primary key field: {pk.name}")
        return normalized
