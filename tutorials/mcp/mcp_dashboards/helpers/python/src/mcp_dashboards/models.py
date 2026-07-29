"""Pydantic models for SQLite metadata and generic CRUD results."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field

_IDENTIFIER_RE = re.compile(r"[^0-9a-zA-Z_]+")


def sanitize_identifier(name: str, *, fallback: str = "col") -> str:
    """Turn an Excel header or sheet name into a safe SQLite identifier."""
    cleaned = _IDENTIFIER_RE.sub("_", (name or "").strip()).strip("_").lower()
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"{fallback}_{cleaned}"
    return cleaned


class ColumnInfo(BaseModel):
    """One column in a table exposed by a dataset MCP server."""

    model_config = ConfigDict(frozen=True)

    name: str
    sqlite_type: str
    nullable: bool = True
    primary_key: bool = False
    autoincrement: bool = False
    source_header: str | None = None


class TableSchema(BaseModel):
    """Schema for one SQLite table, usually one Excel sheet."""

    model_config = ConfigDict(frozen=True)

    name: str
    columns: list[ColumnInfo]
    source_sheet: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def primary_key(self) -> str:
        return self.pk_column.name

    @property
    def pk_column(self) -> ColumnInfo:
        for col in self.columns:
            if col.primary_key:
                return col
        raise ValueError(f"table {self.name!r} has no primary key column")

    @property
    def writable_columns(self) -> list[ColumnInfo]:
        return [c for c in self.columns if not c.autoincrement]

    @property
    def column_names(self) -> frozenset[str]:
        return frozenset(c.name for c in self.columns)

    def get_column(self, name: str) -> ColumnInfo | None:
        key = name.lower()
        for col in self.columns:
            if col.name == key or col.name == name:
                return col
        return None


class BootstrapTableSummary(BaseModel):
    """One table created during Excel to SQLite bootstrap."""

    table: str
    source_sheet: str | None = None
    columns: list[ColumnInfo]
    row_count: int = Field(ge=0)


class BootstrapSummary(BaseModel):
    """Result of seeding SQLite from an Excel workbook."""

    excel_path: Path
    db_path: Path
    tables: list[BootstrapTableSummary]


class DatabaseSchemaDescription(BaseModel):
    """Full live schema description returned by list_schema."""

    db_path: Path
    excel_path: Path
    tables: list[TableSchema]


def _normalize_sort_dir(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


class SortSpec(BaseModel):
    """One ORDER BY clause for typed list tools."""

    field: str = Field(description="Column name from list_schema.")
    dir: Annotated[Literal["asc", "desc"], BeforeValidator(_normalize_sort_dir)] = (
        Field(default="asc")
    )


class ListRowsResult(BaseModel):
    """Paginated row listing for a table."""

    table: str
    count: int = Field(ge=0)
    total_matching: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    search: str | None = None
    search_fields: list[str] = Field(default_factory=list)
    sort: list[SortSpec] = Field(default_factory=list)
    rows: list[dict[str, Any]]


class CountByResult(BaseModel):
    """Grouped COUNT(*) for a column."""

    table: str
    column: str
    total: int = Field(ge=0)
    counts: dict[str, int] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rows(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [
            {"bucket": "__total__", "label": "Total rows", "count": self.total}
        ]
        for key, count in self.counts.items():
            out.append({"bucket": key, "label": key, "count": count})
        return out


class RowResult(BaseModel):
    """Single-row create / get / update response."""

    table: str
    row: dict[str, Any]


class DeleteRowResult(BaseModel):
    """Delete response including the removed row."""

    table: str
    deleted: dict[str, Any]


class ServerStatus(BaseModel):
    """Health-check payload for GET /."""

    server: str = "running"
    dataset: str
    db_path: Path
    excel_path: Path
    tables: list[str] = Field(default_factory=list)
