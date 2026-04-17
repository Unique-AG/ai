# Content folder service

Knowledge-base **folders** are content scopes: they have a `scopeId` (exposed in the toolkit as `scope_id` on :class:`~unique_toolkit.experimental.content_folder.schemas.CreatedFolder` and related models). The :class:`~unique_toolkit.experimental.content_folder.service.ContentFolder` wraps create, read, access changes, and delete calls so you can use the same credentials as the rest of the toolkit (see [Getting started](../../../setup/getting_started.md)).

This page focuses on a **short manual test loop**: create a folder, confirm it exists (API + optional UI), optionally stop in a debugger, then delete it again.

<!--
  Scope: folder (KB) lifecycle and scope-level READ/WRITE via ContentFolder.
  Per-document “content ACL” is usually implied by scope access; Space/assistant
  access is a different API surface (SDK Space resource) if you need it later.
-->

!!! note "Environment"

    Use a working `UniqueSettings` / SDK setup (`UNIQUE_API_KEY`, `UNIQUE_APP_ID`, user and company context) as in other examples. The runnable script below calls :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.from_settings`.

## Ways to create folders

:meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.create_folder` accepts **exactly one** of these shapes per call (mixing them raises ``TypeError``):

| Style | When to use |
|-------|-------------|
| ``path=`` | One absolute path from the KB root, e.g. ``"/Legal/Contracts"``. |
| ``paths=`` | Several absolute paths in one API call. |
| ``parent_scope_id=`` + ``relative_path_segments=`` | You already know the parent folder’s **scope id** and want to create one or more nested segments **by name** (not full paths). |

Segments are **folder names** only—e.g. ``["2026", "Inbox"]`` creates ``Inbox`` under ``2026`` under the given parent—not a second absolute path string.

### Several absolute paths

```{.python #folder-mgmt-constants-multi}
DEMO_MULTI_A = "/EntangledToolkitDocs/MultiA"
DEMO_MULTI_B = "/EntangledToolkitDocs/MultiB"
```

```{.python #folder-mgmt-create-multi-paths}
created = folder_service.create_folder(paths=[DEMO_MULTI_A, DEMO_MULTI_B])
for folder in created:
    print(folder.id, folder.name)
```

```{.python #folder-mgmt-main-multi file=docs/.python_files/folder_create_multiple_abs_paths.py}
<<folder-mgmt-imports>>

<<folder-mgmt-init>>

<<folder-mgmt-constants-multi>>

<<folder-mgmt-create-multi-paths>>
```

??? example "Multiple absolute paths (full script)"

    <!--codeinclude-->
    [Multiple absolute paths](../../../examples_from_docs/folder_create_multiple_abs_paths.py)
    <!--/codeinclude-->

### Under a parent you know by scope id

Typical sources for ``parent_scope_id``:

- The ``id`` on :class:`~unique_toolkit.experimental.content_folder.schemas.CreatedFolder` after an earlier ``create_folder`` (often ``created[-1].id`` for the leaf of a chain).
- The ``id`` on :class:`~unique_toolkit.experimental.content_folder.schemas.FolderInfo` from :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.get_folder_info` (by ``scope_id`` or ``folder_path``).
- Any scope id you already store from the product UI or another API.

Then pass **path segments** (child folder names) to create under that parent:

```{.python #folder-mgmt-constants-nested}
PARENT_ROOT = "/EntangledToolkitDocs/ParentRoot"
```

```{.python #folder-mgmt-create-nested-under-parent}
parent_chain = folder_service.create_folder(path=PARENT_ROOT)
parent_scope_id = parent_chain[-1].id

nested_chain = folder_service.create_folder(
    parent_scope_id=parent_scope_id,
    relative_path_segments=["Projects", "Scratch"],
)
leaf = nested_chain[-1]
print("parent_scope_id=", parent_scope_id)
print("leaf id=", leaf.id, "name=", leaf.name)
```

```{.python #folder-mgmt-main-nested file=docs/.python_files/folder_create_under_parent.py}
<<folder-mgmt-imports>>

<<folder-mgmt-init>>

<<folder-mgmt-constants-nested>>

<<folder-mgmt-create-nested-under-parent>>
```

??? example "Create under parent by scope id (full script)"

    <!--codeinclude-->
    [Create under parent](../../../examples_from_docs/folder_create_under_parent.py)
    <!--/codeinclude-->

### Under a parent you only know by path

If you have the parent’s **absolute path** but not its id, resolve it once, then create by scope id and segments:

```{.python #folder-mgmt-create-nested-after-path-lookup}
parent_meta = folder_service.get_folder_info(folder_path=PARENT_ROOT)
nested = folder_service.create_folder(
    parent_scope_id=parent_meta.id,
    relative_path_segments=["FromPathLookup"],
)
print("leaf", nested[-1].id, nested[-1].name)
```

This is the same API shape as above; only the parent id comes from :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.get_folder_info` instead of a previous create result.

## Create, verify, delete

Typical flow:

1. **Create** with an absolute path from the knowledge-base root (one of the three supported shapes on :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.create_folder`).
2. **Verify** with :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.get_folder_info` using the leaf folder’s `scope_id` (last entry returned from create when the path has multiple segments).
3. **Pause** on a breakpoint or `breakpoint()` after step 2, reload the knowledge-base tree in the product UI, and confirm the folder appears.
4. **Delete** with :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.delete_folder` using the same `scope_id` (or the absolute `folder_path`). Inspect `successFolders` / `failedFolders` on the SDK response if something does not match expectations.

```{.python #folder-mgmt-imports}
from __future__ import annotations

from unique_toolkit.experimental.content_folder import ContentFolder
```

```{.python #folder-mgmt-constants}
# Absolute path from the KB root; change if this collides with real data.
DEMO_FOLDER_PATH = "/EntangledToolkitDocsDemo"
```

```{.python #folder-mgmt-init}
folder_service = ContentFolder.from_settings()
```

```{.python #folder-mgmt-create}
created = folder_service.create_folder(path=DEMO_FOLDER_PATH)
leaf = created[-1]
print(f"Created folder id={leaf.id!r} name={leaf.name!r}")
```

```{.python #folder-mgmt-verify}
info = folder_service.get_folder_info(scope_id=leaf.id)
print(
    f"Verified id={info.id!r} name={info.name!r} parent_id={info.parent_id!r} "
    f"(created as {DEMO_FOLDER_PATH!r}; compare in the UI)"
)
# Set a breakpoint here (IDE or `breakpoint()`) to inspect `info` and confirm in the UI.
```

```{.python #folder-mgmt-delete}
delete_result = folder_service.delete_folder(scope_id=leaf.id)
print("Deleted:", delete_result.get("successFolders"), "Failed:", delete_result.get("failedFolders"))
```

### Assembled runnable script

The block below is tangled to `docs/.python_files/` and copied to [examples_from_docs](../../../examples_from_docs/) when you run `generate_examples.sh` in the `unique_toolkit` package root.

```{.python #folder-mgmt-main file=docs/.python_files/folder_create_verify_delete.py}
<<folder-mgmt-imports>>

<<folder-mgmt-constants>>

<<folder-mgmt-init>>

<<folder-mgmt-create>>

<<folder-mgmt-verify>>

<<folder-mgmt-delete>>
```

??? example "Full example (click to expand)"

    <!--codeinclude-->
    [Create, verify, delete folder](../../../examples_from_docs/folder_create_verify_delete.py)
    <!--/codeinclude-->

## Delete by path

If you prefer to address the folder by path instead of id, pass `folder_path=` (still exactly one of `scope_id` or `folder_path`):

```{.python #folder-mgmt-delete-by-path}
folder_service.delete_folder(folder_path=DEMO_FOLDER_PATH)
```

## Behaviour notes

- **Creator access:** By default, :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.create_folder` grants the acting user READ and WRITE on created scopes when `inherit_access` is false. See the class docstring for details.
- **Recursive delete:** Pass `recursive=True` to :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.delete_folder` when the API should remove nested content according to platform rules.
- **Async:** Use :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.create_folder_async`, :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.get_folder_info_async`, and :meth:`~unique_toolkit.experimental.content_folder.service.ContentFolder.delete_folder_async` in async code paths.

For uploading and searching documents inside a scope, continue with the [Knowledge Base service examples](kb_service.md).
