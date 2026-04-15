from __future__ import annotations

from enum import StrEnum
from typing import Any

from humps import camelize
from pydantic import BaseModel, ConfigDict

model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
)


class FolderAccessType(StrEnum):
    READ = "READ"
    WRITE = "WRITE"


class FolderAccessEntityType(StrEnum):
    USER = "USER"
    GROUP = "GROUP"


class FolderScopeAccess(BaseModel):
    model_config = model_config

    entity_id: str
    type: FolderAccessType
    entity_type: FolderAccessEntityType
    created_at: str | None = None


class FolderChild(BaseModel):
    model_config = model_config

    id: str
    name: str


class IngestionConfig(BaseModel):
    """Configuration controlling how documents in a folder are ingested."""

    model_config = model_config

    unique_ingestion_mode: str
    chunk_max_tokens: int | None = None
    chunk_max_tokens_one_pager: int | None = None
    chunk_min_tokens: int | None = None
    chunk_strategy: str | None = None
    custom_api_options: list[dict[str, Any]] | None = None
    document_min_tokens: int | None = None
    excel_read_mode: str | None = None
    jpg_read_mode: str | None = None
    pdf_read_mode: str | None = None
    ppt_read_mode: str | None = None
    vtt_config: dict[str, Any] | None = None
    word_read_mode: str | None = None


class Folder(BaseModel):
    """Represents a folder with its access rules and children."""

    model_config = model_config

    id: str
    name: str
    scope_access: list[FolderScopeAccess]
    children: list[FolderChild]


class FolderInfo(BaseModel):
    """Metadata about a folder returned by info endpoints."""

    model_config = model_config

    id: str
    name: str
    ingestion_config: IngestionConfig | dict[str, Any]
    created_at: str | None = None
    updated_at: str | None = None
    parent_id: str | None = None
    external_id: str | None = None


class PaginatedFolderInfos(BaseModel):
    model_config = model_config

    folder_infos: list[FolderInfo]
    total_count: int


class CreatedFolder(BaseModel):
    model_config = model_config

    id: str
    object: str
    name: str
    parent_id: str | None = None


class CreateFolderStructureResponse(BaseModel):
    model_config = model_config

    created_folders: list[CreatedFolder]


class DeletedFolderDetail(BaseModel):
    model_config = model_config

    id: str
    name: str
    path: str
    fail_reason: str | None = None


class DeleteFolderResponse(BaseModel):
    model_config = model_config

    success_folders: list[DeletedFolderDetail]
    failed_folders: list[DeletedFolderDetail]


class FolderPath(BaseModel):
    model_config = model_config

    folder_path: str
