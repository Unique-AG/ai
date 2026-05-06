"""Folder (content-scope) management: :class:`ContentFolder`, schemas, and pure helpers.

A knowledge-base folder is a *content scope*; its primary key is ``scopeId`` in the HTTP
API. The toolkit uses **scope_id** for that value everywhere (same string as in responses).

**Creating folders** mirrors the backend in two ways:

- **Absolute paths** — full paths from the root, e.g. ``"/Legal/Contracts"`` (pass ``paths=`` as
  ``str`` or ``list[str]``).
- **Under a parent** — ``parent_scope_id`` plus path **segments** (e.g. ``["2024", "Q1"]``),
  not a second full path string.

By default, :class:`ContentFolder` grants the acting user READ+WRITE on each new folder
(``private_to_creator=True``) unless you inherit parent ACL or opt out—see service docs.

**Classification note (reorg proposal).** The ``private_to_creator`` ACL
grant on create is *toolkit* behavior layered on top of two raw SDK calls
(``Folder.create`` + ``Folder.create_access``), which in isolation would
argue for extracting a ``components/content_acl`` module. It stays inline
here for two reasons: (1) it is opt-out (``private_to_creator=False`` falls
through to pure SDK semantics), and (2) it preserves the common-case
invariant that a creator can read the folder they just created. If more
ACL-shaped behavior (role replacement, bulk reassignment, audit) shows up,
lift it into its own capability then.
"""

from __future__ import annotations

from unique_toolkit.experimental.resources.content_folder.functions import (
    create,
    create_access,
    create_access_async,
    create_async,
    creator_scope_access_grants,
    delete,
    delete_access,
    delete_access_async,
    delete_async,
    read,
    read_async,
)
from unique_toolkit.experimental.resources.content_folder.schemas import (
    AccessEntityType,
    AccessType,
    CreatedFolder,
    DeleteFolderItem,
    DeleteResult,
    FolderChild,
    FolderDetail,
    FolderInfo,
    ScopeAccess,
)
from unique_toolkit.experimental.resources.content_folder.service import ContentFolder

__all__ = [
    "AccessEntityType",
    "AccessType",
    "ContentFolder",
    "CreatedFolder",
    "DeleteFolderItem",
    "DeleteResult",
    "FolderChild",
    "FolderDetail",
    "FolderInfo",
    "ScopeAccess",
    "create",
    "create_access",
    "create_access_async",
    "create_async",
    "creator_scope_access_grants",
    "delete",
    "delete_access",
    "delete_access_async",
    "delete_async",
    "read",
    "read_async",
]
