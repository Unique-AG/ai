"""Pydantic models for schema metadata and MCP CRUD payloads."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    RootModel,
    ValidationError,
    computed_field,
)

from mcp_sqlite_excel import prompts

_IDENTIFIER_RE = re.compile(r"[^0-9a-zA-Z_]+")


def sanitize_identifier(name: str, *, fallback: str = "col") -> str:
    """Turn an Excel header / sheet name into a safe SQL identifier."""
    cleaned = _IDENTIFIER_RE.sub("_", (name or "").strip()).strip("_").lower()
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"{fallback}_{cleaned}"
    return cleaned


class ColumnInfo(BaseModel):
    """One column in a table exposed by the MCP server."""

    model_config = ConfigDict(frozen=True)

    name: str
    sqlite_type: str
    nullable: bool = True
    primary_key: bool = False
    autoincrement: bool = False
    source_header: str | None = None


class TableSchema(BaseModel):
    """Schema for one SQLite table (typically one Excel sheet)."""

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
    """One table created during Excel → SQLite bootstrap."""

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
    """Lowercase sort direction so agents may send ASC/DESC."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


class SortSpec(BaseModel):
    """One ORDER BY clause for list_rows."""

    field: str = Field(description="Column name from list_schema.")
    # Use an enum (not a Python ``(?i)`` regex): Unique's JS bridge compiles
    # JSON Schema patterns and rejects inline ``(?i)`` flags.
    dir: Annotated[Literal["asc", "desc"], BeforeValidator(_normalize_sort_dir)] = Field(
        default="asc",
        description='Sort direction: "asc" or "desc".',
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
    """Grouped COUNT(*) for a column (e.g. status KPI tiles)."""

    table: str
    column: str
    total: int = Field(ge=0)
    counts: dict[str, int] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rows(self) -> list[dict[str, Any]]:
        """Canvas-friendly rows for ``data-unique-source-path="rows"`` KPI tiles."""
        out: list[dict[str, Any]] = [{"bucket": "__total__", "label": "Total clients", "count": self.total}]
        for key, n in self.counts.items():
            out.append({"bucket": key, "label": key, "count": n})
        return out


class RowResult(BaseModel):
    """Single-row create / get / update response."""

    table: str
    row: dict[str, Any]


class DeleteRowResult(BaseModel):
    """Delete response including the removed row."""

    table: str
    deleted: dict[str, Any]


class ToolError(BaseModel):
    """Structured error returned from MCP tool handlers."""

    error: str
    message: str


class EscalateForm(BaseModel):
    """Elicitation form shown when escalating a row (status/state → Escalated)."""

    recipient_email: str = Field(
        default=prompts.DEFAULT_ESCALATE_RECIPIENT_EMAIL,
        description="Email address of the person who should be notified about this escalation.",
        min_length=3,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    note: str = Field(
        default=prompts.DEFAULT_ESCALATE_NOTE,
        description="Note to include in the escalation email.",
    )


class EscalationEmailNotice(BaseModel):
    """Record of the escalation notification that was (demo-)sent."""

    to: str
    note: str = ""
    subject: str
    sent: bool = True


class EscalateUpdateResult(BaseModel):
    """update_row response when an escalation was confirmed and notified."""

    table: str
    row: dict[str, Any]
    escalation_email: EscalationEmailNotice


class ServerStatus(BaseModel):
    """Health-check payload for GET /."""

    server: str = "running"
    auth_disabled: bool
    db_path: Path
    excel_path: Path
    tables: list[str] = Field(default_factory=list)


class FieldMap(RootModel[dict[str, Any]]):
    """JSON object of column → value used for filters and writes."""

    root: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_mcp_arg(cls, value: str | dict[str, Any] | None, *, field_name: str) -> FieldMap:
        """Parse an MCP tool argument that may be a dict or JSON object string."""
        if value is None:
            return cls({})
        if isinstance(value, dict):
            return cls(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return cls({})
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{field_name} must be a JSON object: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError(f"{field_name} must be a JSON object")
            try:
                return cls.model_validate(parsed)
            except ValidationError as exc:
                raise ValueError(f"{field_name} must be a JSON object: {exc}") from exc
        raise TypeError(f"{field_name} must be a dict or JSON object string")


def parse_sort_arg(value: list[Any] | str | None, *, field_name: str = "sort") -> list[SortSpec]:
    """Parse list_rows sort from a list or JSON array string."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name} must be a JSON array: {exc}") from exc
        value = parsed
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of {{field, dir}} objects")
    try:
        return [SortSpec.model_validate(item) for item in value]
    except ValidationError as exc:
        raise ValueError(f"{field_name} must be a list of {{field, dir}} objects: {exc}") from exc


def parse_search_fields_arg(
    value: list[Any] | str | None,
    *,
    field_name: str = "search_fields",
) -> list[str] | None:
    """Parse optional search_fields list; None means use table defaults."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name} must be a JSON array of column names: {exc}") from exc
        value = parsed
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of column name strings")
    return [str(item) for item in value]
