# Architectural Design Decisions

This document captures architectural design decisions (ADRs) for the
`unique_toolkit`. Each decision describes the context, the rule we want to
enforce, and the current status of the codebase against it. New decisions are
appended; existing ones are amended rather than replaced.

> ADR status legend: `Proposed` → `Accepted` → `Deprecated`/`Superseded`.

---

## ADR-0001 — Public API naming: CRUD verbs and plural arguments

Status: **Accepted**

Scope: Any public function / service method in `unique_toolkit` that wraps an
`unique_sdk` resource (including `functions.py` and the `*Service` classes).

### Context

As we promote functionality from `unique_sdk` into `unique_toolkit`, the public
surface becomes the long-lived contract that apps, tools and the orchestrator
depend on. Inconsistent verbs (`modify_*`, `find_*`, `request_*`, `remove_*`,
`replace_*`, `set`/`get`) and mixed singular/plural arguments (`path` vs
`paths`, `content_id` vs `content_ids`) make the API harder to learn, harder
to auto-complete, and harder to evolve without breaking changes.

### Decision

1. **Use proper CRUD verbs for function names.** The canonical verbs are:

    | Operation | Verb(s)                                            |
    | --------- | -------------------------------------------------- |
    | Create    | `create_*`                                         |
    | Read      | `get_*` (by id/fixed key), `list_*` (collections), `search_*` (query) |
    | Update    | `update_*` (partial), `replace_*` (full, PUT-like) |
    | Delete    | `delete_*`                                         |

    Avoid: `modify_*`, `find_*`, `request_*`, `remove_*`, `fetch_*`, `set`,
    `put_*` — they duplicate the verbs above with unclear semantics. Domain
    verbs (`upload_*`, `download_*`, `embed_*`, `complete_*`, `stream_*`,
    `enable_*`, `disable_*`) stay where the action is not a CRUD operation
    on a resource.

2. **Use plurals for arguments that are a list.**
    `paths: list[PurePath]`, `content_ids: list[str]`,
    `keys_to_remove: list[str]`, `texts: list[str]`.

3. **Use plurals for arguments that can be a list or a singular.** When a
    parameter accepts both shapes, prefer the plural name and the union type:

    ```python
    def delete_contents(*, paths: str | list[str]) -> ...
    ```

    A singular overload (`delete_content(*, path: str)`) may coexist when
    clarity benefits the caller, but the plural form is the canonical one.

4. **Mirror the name in async variants** with an `_async` suffix
    (`create_message` / `create_message_async`).

5. **Prefer keyword-only arguments** (`*,` in the signature) for all
    parameters beyond `self`. This keeps call-sites readable and lets us add
    or reorder parameters without silent breakage.

### Consequences

- New and renamed functions MUST follow these rules.
- Existing functions that do not comply are tracked in the
  [API audit](#api-audit-current-mismatches) below. Each mismatch is either
  renamed with a deprecation alias or explicitly justified and kept.
- Breaking renames go through a deprecation cycle: add the new name, keep
  the old as a thin wrapper that emits `DeprecationWarning`, remove on the
  next major bump.

---

## API audit — current mismatches

Snapshot of the public API as of this ADR. "Proposed" is the rename we want
to apply; `—` means the existing name already complies. `*` marks async
twins that follow the same rename.

### `ChatService` (`unique_toolkit/services/chat_service.py`)

| Current name                         | Issue                              | Proposed rename                     |
| ------------------------------------ | ---------------------------------- | ----------------------------------- |
| `modify_user_message`*               | `modify_*` is not CRUD             | `update_user_message`               |
| `modify_assistant_message`*          | `modify_*` is not CRUD             | `update_assistant_message`          |
| `modify_message_assessment`*         | `modify_*` is not CRUD             | `update_message_assessment`         |
| `replace_debug_info`                 | non-standard verb                  | `update_debug_info` (or keep `replace_` with PUT semantics, pair with `update_debug_info` for PATCH) |
| `find_chat_memory_by_id`*            | `find_*` is not CRUD               | `get_chat_memory_by_id`             |
| `find_chat_memory`*                  | `find_*` is not CRUD               | `get_chat_memory`                   |
| `find_message_memory_by_id`*         | `find_*` is not CRUD               | `get_message_memory_by_id`          |
| `find_message_memory`*               | `find_*` is not CRUD               | `get_message_memory`                |
| `get_full_history`*                  | —                                  | —                                   |
| `get_full_and_selected_history`*     | —                                  | —                                   |
| `get_debug_info`*                    | —                                  | —                                   |
| `get_message_execution`*             | —                                  | —                                   |
| `get_assistant_message_execution`*   | —                                  | —                                   |
| `get_message_tools`*                 | —                                  | —                                   |
| `create_*`, `update_*` (executions, logs, tools, memory) | — | —                                   |
| `upload_to_chat_from_bytes`*         | domain verb, acceptable            | —                                   |
| `download_chat_content_to_bytes`*    | domain verb, acceptable            | —                                   |
| `download_chat_images_and_documents` | returns a tuple of lists; reads    | `list_chat_images_and_documents`    |
| `free_user_input`                    | domain action, acceptable          | —                                   |
| `stream_complete`*, `complete`*, `complete_with_references`*, `complete_responses_with_references`* | domain verbs | — |

### `KnowledgeBaseService` (`unique_toolkit/services/knowledge_base.py`)

| Current name                  | Issue                                          | Proposed rename / action                       |
| ----------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| `search_content_chunks`*      | —                                              | —                                              |
| `search_contents`*            | —                                              | —                                              |
| `upload_content`*, `upload_content_from_bytes`* | domain verbs                    | —                                              |
| `download_content_to_file`, `download_content_to_bytes`* | domain verbs         | —                                              |
| `batch_file_upload`           | not CRUD / not plural-argument shape           | `upload_files(*, local_files, remote_folders)` (already plural args; rename) |
| `get_paginated_content_infos`*, `get_content_infos_async`, `get_file_names_in_folder`, `get_folder_info`* | — | — |
| `create_folders`              | — (takes `paths: list[PurePath]`, plural ✔)    | —                                              |
| `replace_content_metadata`    | PUT semantics; keep but document intent        | keep, ensure docstring distinguishes from `update_` |
| `update_content_metadata`*    | —                                              | —                                              |
| `remove_content_metadata`     | `remove_*` is not CRUD                         | `delete_content_metadata` (keys form partial delete) |
| `update_contents_metadata`    | — (plural)                                     | —                                              |
| `remove_contents_metadata`    | `remove_*` is not CRUD                         | `delete_contents_metadata`                     |
| `delete_content`*             | singular variant via overloads                 | keep singular overload; canonical is `delete_contents` |
| `delete_contents`*            | takes `metadata_filter` only; should also accept plural ids/paths | extend to `*, content_ids: str \| list[str] \| None, paths: str \| list[str] \| None, metadata_filter: dict \| None` |
| `resolve_visible_file_paths_async` | read-like, acceptable                     | —                                              |
| `get_folder_path`, `get_scope_id_path` | —                                      | —                                              |

### `ContentService` (`unique_toolkit/content/service.py`, legacy)

Marked as deprecated in favor of `KnowledgeBaseService`, but still shipped.

| Current name                         | Issue                                   | Proposed rename                    |
| ------------------------------------ | --------------------------------------- | ---------------------------------- |
| `request_content_by_id`              | `request_*` is not CRUD                 | `get_content_by_id`                |
| `search_content_on_chat`             | returns a `list[Content]` but name is singular | `search_contents_on_chat`   |
| `get_documents_uploaded_to_chat`     | —                                       | — (or `list_chat_documents`)       |
| `get_images_uploaded_to_chat`        | —                                       | — (or `list_chat_images`)          |
| `upload_content`, `upload_content_from_bytes`* | domain verbs                  | —                                  |
| `download_content`, `download_content_to_file_by_id`, `download_content_to_bytes`* | domain verbs | —    |
| `is_file_content`, `is_image_content`| predicate, acceptable                   | —                                  |

> Because this module is deprecated, renames here are only applied if they
> already exist in `KnowledgeBaseService`. Otherwise we deprecate the whole
> method instead of renaming it twice.

### `ShortTermMemoryService` (`unique_toolkit/short_term_memory/service.py`)

| Current name                | Issue                           | Proposed rename                     |
| --------------------------- | ------------------------------- | ----------------------------------- |
| `find_latest_memory`*       | `find_*` is not CRUD            | `get_latest_memory`                 |
| `create_memory`*            | —                               | —                                   |
| `set(key, value)`           | not CRUD; positional args       | `create_memory(*, key, value)` (already exists); remove `set` alias |
| `get(key)`                  | too generic; positional         | `get_latest_memory(*, key)` (align with above); remove `get` alias |
| Positional `(key, value)` signatures | violates keyword-only rule | move to `*, key: str, value: ...`   |

### `EmbeddingService` (`unique_toolkit/embedding/service.py`)

| Current name    | Issue | Proposed rename |
| --------------- | ----- | --------------- |
| `embed_texts`*  | domain verb, plural argument ✔ | — |

Marked as "to be moved" in the architecture doc; no renames planned.

### `ScheduledTaskService` (`unique_toolkit/experimental/scheduled_task/service.py`)

Reference implementation for this ADR — already follows the convention:

| Current name    | Status |
| --------------- | ------ |
| `create`*       | ✔      |
| `list`*         | ✔      |
| `get`*          | ✔      |
| `update`*       | ✔      |
| `delete`*       | ✔      |
| `enable`*, `disable`* | ✔ (domain actions) |

---

## Rollout plan

1. Add the canonical name next to the current one; mark the current one with
   `@deprecated` / `DeprecationWarning`.
2. Update examples and docs under `unique_toolkit/docs/` to the new names.
3. Remove the deprecated names at the next major version bump (tracked per
   service in `CHANGELOG.md`).
