"""Folder (content-scope) management: :class:`ContentFolder`, schemas, and pure helpers.

A knowledge-base folder is a *content scope*; its primary key is ``scopeId`` in the HTTP
API. The toolkit uses **scope_id** for that value everywhere (same string as in responses).

**Creating folders** mirrors the backend in two ways:

- **Absolute paths** — full paths from the root, e.g. ``"/Legal/Contracts"``.
- **Under a parent** — ``parent_scope_id`` plus path **segments** (e.g. ``["2024", "Q1"]``),
  not a second full path string.

By default, :class:`ContentFolder` grants the acting user READ+WRITE on each new folder
(``private_to_creator=True``) unless you inherit parent ACL or opt out—see service docs.
"""

from __future__ import annotations

from unique_toolkit.experimental.content_folder.functions import (
    add_folder_access,
    add_folder_access_async,
    create_folders,
    create_folders_async,
    creator_scope_access_grants,
    delete_folder,
    delete_folder_async,
    get_folder_info,
    get_folder_info_async,
    remove_folder_access,
    remove_folder_access_async,
)
from unique_toolkit.experimental.content_folder.schemas import (
    AccessEntityType,
    AccessType,
    CreatedFolder,
    FolderChild,
    FolderDetail,
    FolderInfo,
    ScopeAccess,
)
from unique_toolkit.experimental.content_folder.service import ContentFolder

__all__ = [
    "AccessEntityType",
    "AccessType",
    "ContentFolder",
    "CreatedFolder",
    "FolderChild",
    "FolderDetail",
    "FolderInfo",
    "ScopeAccess",
    "add_folder_access",
    "add_folder_access_async",
    "create_folders",
    "create_folders_async",
    "creator_scope_access_grants",
    "delete_folder",
    "delete_folder_async",
    "get_folder_info",
    "get_folder_info_async",
    "remove_folder_access",
    "remove_folder_access_async",
]
