"""Pydantic models for knowledge-base folders (content scopes).

These mirror the ``Folder`` resources returned by the Unique API and are the
value types exchanged with :class:`~unique_toolkit.experimental.content_folder.service.ContentFolder`
and the helpers in :mod:`unique_toolkit.experimental.content_folder.functions`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


class AccessType(StrEnum):
    """Permission level on a folder (content scope); matches ``Folder.ScopeAccess.type`` in the API."""

    READ = "READ"
    WRITE = "WRITE"


class AccessEntityType(StrEnum):
    """Principal kind for a folder ACL entry; matches ``Folder.ScopeAccess.entityType``."""

    USER = "USER"
    GROUP = "GROUP"


class ScopeAccess(BaseModel):
    """One ACL row for a knowledge-base folder (API field ``scopeAccess``).

    **What ``entity_id`` is:** It is always either a **user id** or a **group id**, depending on
    ``entity_type``. It is **not** a company id—company context comes from the authenticated
    SDK call (``company_id``). Use ids from the User / Group APIs or from your directory sync.

    **What ``type`` is:** ``READ`` (list/read content in the scope) or ``WRITE`` (upload, change,
    or delete within the scope), per the backend folder-access model—not the same as Space
    access (``USE`` / ``MANAGE`` / ``UPLOAD`` on assistants).
    """

    model_config = model_config

    entity_id: str = Field(
        description=(
            "When ``entity_type`` is ``USER``, the Unique **user id** to grant. "
            "When ``entity_type`` is ``GROUP``, the **group id**. Never a company id."
        ),
    )
    type: AccessType = Field(
        description="Folder-level permission: READ or WRITE for this principal.",
    )
    entity_type: AccessEntityType = Field(
        description="Whether ``entity_id`` refers to a user or a group.",
    )
    created_at: str | None = Field(
        default=None,
        description="ISO timestamp when the grant was created; usually present on API responses, omit when adding access.",
    )


class CreatedFolder(BaseModel):
    """Single folder returned from create-paths (API ``createdFolders`` items)."""

    model_config = model_config

    id: str = Field(
        description="Scope id of the folder (same as HTTP ``scopeId``).",
    )
    object: str = Field(
        description="Object type discriminator from the API (e.g. folder resource name).",
    )
    name: str = Field(
        description="Leaf segment name of the folder that was created or resolved.",
    )
    parent_id: str | None = Field(
        default=None,
        description="Scope id of the parent folder, if any.",
    )


class FolderInfo(BaseModel):
    """Folder metadata from ``GET /folder/info`` (API ``FolderInfo``)."""

    model_config = model_config

    id: str = Field(description="Scope id of the folder.")
    name: str = Field(description="Display name / leaf segment of the folder.")
    ingestion_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Ingestion settings for this scope (chunking, read modes, etc.).",
    )
    created_at: str | None = Field(
        default=None,
        description="Creation time from the API, if returned.",
    )
    updated_at: str | None = Field(
        default=None,
        description="Last update time from the API, if returned.",
    )
    parent_id: str | None = Field(
        default=None,
        description="Parent folder scope id, if not a root folder.",
    )
    external_id: str | None = Field(
        default=None,
        description="Optional external identifier linked to this folder, if configured.",
    )


class FolderChild(BaseModel):
    """Lightweight child reference in a folder listing."""

    model_config = model_config

    id: str = Field(description="Child folder scope id.")
    name: str = Field(description="Child folder name.")


class FolderDetail(BaseModel):
    """Folder object including nested access list and child folders (typical add/remove-access response shape)."""

    model_config = model_config

    id: str = Field(description="Scope id of this folder.")
    name: str = Field(description="Folder name.")
    scope_access: list[ScopeAccess] = Field(
        default_factory=list,
        description="Effective READ/WRITE grants for users and groups on this folder.",
    )
    children: list[FolderChild] = Field(
        default_factory=list,
        description="Immediate child folders (id + name).",
    )
