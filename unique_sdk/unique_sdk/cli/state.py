"""Shell state tracking the current working directory (path + scope_id)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk.cli.config import Config

_SEARCH_CONFIG_FILENAME = ".unique-search.json"
_CHAT_FILES_MANIFEST_PATH = Path(".unique") / "chat-files.json"

# A Unique folder scope id, e.g. ``scope_ch5tigpwhamry2dqimxl3a7a``. Used to
# extract the target folder from a ``folderIdPath`` filter value, which is
# either a bare ``scope_…`` or a ``uniquepathid://scope_root/scope_leaf`` path
# (segments are ``/``-separated, so matching is bounded by the path separator).
_SCOPE_ID_RE = re.compile(r"scope_[a-z0-9_]+", re.IGNORECASE)


def _load_search_config() -> dict[str, Any]:
    """Load ``.unique-search.json`` from the cwd, or ``{}`` when absent/invalid."""
    config_path = Path.cwd() / _SEARCH_CONFIG_FILENAME
    if not config_path.is_file():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_workspace_scope_ids(data: dict[str, Any]) -> list[str]:
    scope_ids = data.get("scopeIds")
    if isinstance(scope_ids, list) and all(isinstance(s, str) for s in scope_ids):
        return scope_ids
    return []


def _load_workspace_metadata_filter(data: dict[str, Any]) -> dict[str, Any] | None:
    """Per-message UniqueQL scope written by the Swappable Intelligence runner.

    When present (e.g. from an Agentic Table column's ``scope_rules``), it
    expresses scopes a flat ``scopeIds`` list cannot — recursive folder
    CONTAINS, contentId IN, boolean trees — and takes precedence over the
    static ``scopeIds``. See UN-21780.
    """
    metadata_filter = data.get("metaDataFilter")
    return (
        metadata_filter
        if isinstance(metadata_filter, dict) and metadata_filter
        else None
    )


def _load_chat_file_content_ids() -> set[str]:
    """Content IDs of files attached to this chat, from ``.unique/chat-files.json``.

    The Swappable Intelligence runner downloads chat-attached files into the
    workspace and writes a ``{filename: contentId}`` manifest. These are turn
    *inputs* (e.g. an Agentic Table row's question file), not knowledge-base
    documents, so they must stay readable regardless of the per-message KB
    scope filter. Returns an empty set when the manifest is absent or invalid.
    """
    path = Path.cwd() / _CHAT_FILES_MANIFEST_PATH
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    if not isinstance(data, dict):
        return set()
    return {v for v in data.values() if isinstance(v, str) and v.startswith("cont_")}


def _extract_target_scope_id(value: Any) -> str | None:
    """Deepest folder scope id referenced by a ``folderIdPath`` filter value.

    Values are either a bare ``scope_…`` or a
    ``uniquepathid://scope_root/scope_leaf`` path. ``folderIdPath contains``
    means "anywhere under the leaf folder", so the last ``scope_…`` token is
    the folder being scoped to.
    """
    if not isinstance(value, str):
        return None
    matches = _SCOPE_ID_RE.findall(value)
    return matches[-1] if matches else None


def _is_negated_operator(operator: Any) -> bool:
    """True for exclusion operators (notIn, notEquals, notContains, …)."""
    return isinstance(operator, str) and operator.lower().startswith("not")


def _collect_filter_targets(
    node: Any,
    folder_ids: list[str] | None = None,
    content_ids: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Collect every folder scope id and content id referenced by a filter tree.

    Order-preserving and de-duplicated. Used to *describe* the active scope
    (for ``ls`` and denial hints) without enumerating folder contents.
    """
    if folder_ids is None:
        folder_ids = []
    if content_ids is None:
        content_ids = []
    if not isinstance(node, dict):
        return folder_ids, content_ids
    for key in ("and", "or"):
        if key in node:
            for child in node.get(key) or []:
                _collect_filter_targets(child, folder_ids, content_ids)
            return folder_ids, content_ids

    path = node.get("path")
    field = path[0] if isinstance(path, list) and path else path
    value = node.get("value")
    if _is_negated_operator(node.get("operator")):
        # Negated leaves (notIn, notEquals, notContains) are *exclusions*;
        # listing their targets as in-scope would invert their meaning
        # (e.g. an Agentic Table question_file_ids notIn rule).
        return folder_ids, content_ids
    if field == "contentId":
        values = value if isinstance(value, list) else [value]
        for v in values:
            if isinstance(v, str) and v.startswith("cont_") and v not in content_ids:
                content_ids.append(v)
    elif field == "folderIdPath":
        values = value if isinstance(value, list) else [value]
        for v in values:
            scope_id = _extract_target_scope_id(v)
            if scope_id and scope_id not in folder_ids:
                folder_ids.append(scope_id)
    return folder_ids, content_ids


class ShellState:
    """Tracks the virtual working directory within the Unique folder hierarchy."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._path = "/"
        self._scope_id: str | None = None
        _search_config = _load_search_config()
        self.workspace_scope_ids: list[str] = _load_workspace_scope_ids(_search_config)
        self.workspace_metadata_filter: dict[str, Any] | None = (
            _load_workspace_metadata_filter(_search_config)
        )
        self._workspace_scope_paths: list[str] | None = None
        # Per-turn caches for per-message metadata-filter content gating. Keyed
        # by id; populated lazily so repeated reads/cites of the same document
        # cost at most one resolution per turn. See UN-21780.
        self._scope_path_cache: dict[str, str | None] = {}
        self._content_owner_path_cache: dict[str, str | None] = {}
        self._mdf_verdict_cache: dict[str, bool] = {}
        self._chat_file_content_ids_cache: set[str] | None = None
        # Raw ``Content.get_info`` item per content id, shared by the scope
        # gate (owner path) and citation title resolution so a read+cite of
        # the same document costs one info call per turn. See UN-21780.
        self._content_info_cache: dict[str, unique_sdk.Content.ContentInfo | None] = {}

    @property
    def workspace_restricted(self) -> bool:
        return bool(self.workspace_scope_ids)

    def _resolve_workspace_scope_paths(self) -> list[str]:
        """Lazily resolve workspace scope IDs to folder paths (one API call per scope, cached)."""
        if self._workspace_scope_paths is not None:
            return self._workspace_scope_paths
        paths: list[str] = []
        for scope_id in self.workspace_scope_ids:
            try:
                resp = unique_sdk.Folder.get_folder_path(
                    user_id=self.config.user_id,
                    company_id=self.config.company_id,
                    scope_id=scope_id,
                )
                p = resp.get("folderPath", "").rstrip("/")
                if p:  # empty after rstrip means the API returned "/" (root) — skip
                    paths.append(p)
            except Exception:
                pass
        self._workspace_scope_paths = paths
        return paths

    def is_within_workspace(self) -> bool:
        """Return True if the current path is inside (or is) a workspace scope root.

        Always returns True when no workspace restriction is configured.
        """
        if not self.workspace_scope_ids:
            return True
        if self._scope_id in self.workspace_scope_ids:
            return True
        paths = self._resolve_workspace_scope_paths()
        if not paths:
            return False
        current = self._path
        return any(current == p or current.startswith(p + "/") for p in paths)

    def is_content_within_workspace(self, content_id: str) -> bool:
        """Return True if *content_id* is readable in the current workspace scope.

        Precedence (UN-21780):
        1. A per-message UniqueQL ``metaDataFilter`` (e.g. an Agentic Table
           column's ``scope_rules``) is the authority for this turn and
           *replaces* the static ``scopeIds`` for content access. Files the
           caller attached to the chat are turn inputs and stay readable.
        2. Otherwise the static ``scopeIds`` boundary applies (one API call to
           resolve the content's parent scope, then
           ``is_folder_target_within_workspace``).
        3. With neither configured, everything is in scope.
        """
        if self.workspace_metadata_filter is not None:
            if content_id in self._chat_file_content_ids():
                return True
            return self.content_allowed_by_metadata_filter(content_id)
        if not self.workspace_scope_ids:
            return True
        try:
            result = unique_sdk.Content.get_info(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                contentId=content_id,
            )
            items = result.get("contentInfo", [])
            if not items:
                return False
            owner_id = items[0].get("ownerId", "")
            return self.is_folder_target_within_workspace(owner_id)
        except Exception:
            return False

    def is_folder_target_within_workspace(self, target: str) -> bool:
        """Check whether a folder target is within the workspace.

        For scope IDs and absolute paths the *target itself* is validated,
        not the current working directory.  Relative names fall back to the
        CWD check because they always resolve under the current directory.

        Always returns True when no workspace restriction is configured.
        """
        if not self.workspace_scope_ids:
            return True

        if target.startswith("scope_"):
            if target in self.workspace_scope_ids:
                return True
            paths = self._resolve_workspace_scope_paths()
            if not paths:
                return False
            try:
                resp = unique_sdk.Folder.get_folder_path(
                    user_id=self.config.user_id,
                    company_id=self.config.company_id,
                    scope_id=target,
                )
                p = resp.get("folderPath", "")
                return any(p == wp or p.startswith(wp + "/") for wp in paths)
            except Exception:
                return False

        if target.startswith("/"):
            # Normalize to collapse any `..` components before prefix-checking.
            # Without this, "/Workspace/../Evil" would pass a startswith("/Workspace/") check.
            normalized = os.path.normpath(target)
            paths = self._resolve_workspace_scope_paths()
            if not paths:
                return False
            return any(normalized == p or normalized.startswith(p + "/") for p in paths)

        # Relative path — resolve against CWD so that `../../outside` style
        # traversals are caught rather than delegating blindly to the CWD check.
        resolved = os.path.normpath(self._path.rstrip("/") + "/" + target)
        paths = self._resolve_workspace_scope_paths()
        if not paths:
            return self._scope_id in self.workspace_scope_ids
        return any(resolved == p or resolved.startswith(p + "/") for p in paths)

    # ── Per-message metadata-filter content gating (UN-21780) ──────────────

    def _chat_file_content_ids(self) -> set[str]:
        """Content IDs attached to this chat (turn inputs), cached per turn."""
        if self._chat_file_content_ids_cache is None:
            self._chat_file_content_ids_cache = _load_chat_file_content_ids()
        return self._chat_file_content_ids_cache

    def _resolve_scope_path(self, scope_id: str) -> str | None:
        """Resolve a folder scope id to its absolute folder path (cached)."""
        if scope_id in self._scope_path_cache:
            return self._scope_path_cache[scope_id]
        path: str | None = None
        try:
            resp = unique_sdk.Folder.get_folder_path(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                scope_id=scope_id,
            )
            stripped = (resp.get("folderPath") or "").rstrip("/")
            path = stripped or None
        except Exception:
            path = None
        self._scope_path_cache[scope_id] = path
        return path

    def _resolve_content_owner_path(self, content_id: str) -> str | None:
        """Resolve a content's owning folder path (cached).

        One ``Content.get_info`` (owner scope) plus one
        ``Folder.get_folder_path`` (owner → path), both memoised on this
        ``ShellState`` so repeated reads/cites of the same document within a
        turn cost nothing after the first.
        """
        if content_id in self._content_owner_path_cache:
            return self._content_owner_path_cache[content_id]
        owner_path: str | None = None
        info = self._get_content_info(content_id)
        owner_id = info.get("ownerId", "") if info else ""
        if owner_id:
            owner_path = self._resolve_scope_path(owner_id)
        self._content_owner_path_cache[content_id] = owner_path
        return owner_path

    def _get_content_info(
        self, content_id: str
    ) -> unique_sdk.Content.ContentInfo | None:
        """Return the cached ``Content.get_info`` item for *content_id*.

        One API call per content id per turn, memoised on this ``ShellState``
        and shared between owner-path scope checks and citation title lookup.
        """
        if content_id in self._content_info_cache:
            return self._content_info_cache[content_id]
        info: unique_sdk.Content.ContentInfo | None = None
        try:
            result = unique_sdk.Content.get_info(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                contentId=content_id,
            )
            items = result.get("contentInfo", [])
            info = items[0] if items else None
        except Exception:
            info = None
        self._content_info_cache[content_id] = info
        return info

    def resolve_content_title(self, content_id: str) -> str:
        """Human-readable title for a content id, falling back to the id.

        Mirrors the ``title or key`` convention used by ``read`` and ``ls`` so
        citations made by bare ``cont_*`` id still render with the document's
        filename instead of the opaque id. See UN-21780.
        """
        info = self._get_content_info(content_id)
        if not info:
            return content_id
        return info.get("title") or info.get("key") or content_id

    def content_allowed_by_metadata_filter(self, content_id: str) -> bool:
        """Return True if *content_id* satisfies the per-message scope filter.

        Evaluates the UniqueQL ``metaDataFilter`` written to
        ``.unique-search.json`` against a single document, so file reads/cites
        honour the same per-turn scope as ``unique-cli search`` (UN-21780).

        Only the two *scope-boundary* leaf types are enforced locally:
        ``contentId`` membership (free) and ``folderIdPath`` containment
        (resolves the document's owning folder, cached). Non-boundary leaves
        (e.g. ``mimeType``) are treated as non-restrictive here — the search
        server still enforces the full filter for KB search. Returns True when
        no filter is configured.
        """
        if not self.workspace_metadata_filter:
            return True
        if content_id in self._mdf_verdict_cache:
            return self._mdf_verdict_cache[content_id]
        verdict = self._eval_filter_node(self.workspace_metadata_filter, content_id)
        self._mdf_verdict_cache[content_id] = verdict
        return verdict

    def _eval_filter_node(self, node: Any, content_id: str) -> bool:
        if not isinstance(node, dict):
            return True
        if "and" in node:
            return all(
                self._eval_filter_node(c, content_id) for c in (node.get("and") or [])
            )
        if "or" in node:
            children = node.get("or") or []
            if not children:
                return True
            # Cheap contentId leaves first so an OR can short-circuit to True
            # without a folder-ancestry lookup.
            ordered = sorted(children, key=self._leaf_cost)
            return any(self._eval_filter_node(c, content_id) for c in ordered)
        return self._eval_leaf(node, content_id)

    @staticmethod
    def _leaf_cost(node: Any) -> int:
        """Sort key: 0 for free (contentId) leaves, 1 otherwise."""
        if isinstance(node, dict):
            path = node.get("path")
            field = path[0] if isinstance(path, list) and path else path
            if field == "contentId":
                return 0
        return 1

    def _eval_leaf(self, node: dict[str, Any], content_id: str) -> bool:
        path = node.get("path")
        field = path[0] if isinstance(path, list) and path else path
        value = node.get("value")
        negated = _is_negated_operator(node.get("operator"))
        if field == "contentId":
            if isinstance(value, list):
                matched = content_id in value
            else:
                matched = content_id == value
            # A negated leaf (notIn/notEquals) is an exclusion: membership
            # must deny, not grant (e.g. Agentic Table question_file_ids).
            return not matched if negated else matched
        if field == "folderIdPath":
            owner_path = self._resolve_content_owner_path(content_id)
            if owner_path is None:
                return False
            targets = value if isinstance(value, list) else [value]
            contained = False
            for target in targets:
                scope_id = _extract_target_scope_id(target)
                if not scope_id:
                    continue
                target_path = self._resolve_scope_path(scope_id)
                if target_path and (
                    owner_path == target_path
                    or owner_path.startswith(target_path + "/")
                ):
                    contained = True
                    break
            return not contained if negated else contained
        # Non-boundary leaf (e.g. mimeType, language): not a folder/content
        # access boundary, so not enforced locally. The search server still
        # applies it for KB search.
        return True

    def folder_allowed_by_metadata_filter(self, scope_id: str) -> bool:
        """True if *scope_id* is inside one of the filter's folder scopes.

        Gates explicit folder targets (e.g. ``ls <path>``) so navigation
        cannot enumerate folders outside the per-message scope. Documents
        scoped individually (``contentId in``) don't grant folder listings.
        Returns True when no per-message filter is configured.
        """
        if not self.workspace_metadata_filter:
            return True
        folder_paths, _ = self.metadata_filter_scope()
        if not folder_paths:
            return False
        target_path = self._resolve_scope_path(scope_id)
        if not target_path:
            return False
        return any(
            target_path == p or target_path.startswith(p + "/") for p in folder_paths
        )

    def metadata_filter_scope(self) -> tuple[list[str], list[str]]:
        """Return ``(folder_paths, content_ids)`` referenced by the filter.

        Folder scope ids are resolved to absolute paths (cached); content ids
        are returned verbatim. Used to *describe* the active scope to the agent
        (``ls`` at root, denial hints) without enumerating folder contents.
        Returns empty lists when no per-message filter is configured.
        """
        if not self.workspace_metadata_filter:
            return [], []
        folder_ids, content_ids = _collect_filter_targets(
            self.workspace_metadata_filter
        )
        paths: list[str] = []
        for scope_id in folder_ids:
            resolved = self._resolve_scope_path(scope_id)
            if resolved:
                paths.append(resolved)
        return paths, content_ids

    def scope_denial_hint(self) -> str:
        """One-line description of the active scope, for denial messages.

        Steers the agent back to in-scope folders/documents instead of
        prompting blind retries on out-of-scope content.
        """
        if self.workspace_metadata_filter is not None:
            folders, content_ids = self.metadata_filter_scope()
            parts: list[str] = []
            if folders:
                parts.append("folders: " + ", ".join(folders))
            if content_ids:
                shown = ", ".join(content_ids[:5])
                more = (
                    "" if len(content_ids) <= 5 else f" (+{len(content_ids) - 5} more)"
                )
                parts.append(f"documents: {shown}{more}")
            return "; ".join(parts) if parts else "the task's configured scope"
        paths = self._resolve_workspace_scope_paths()
        if paths:
            return "folders: " + ", ".join(paths)
        return "the workspace scope"

    @property
    def cwd(self) -> str:
        return self._path

    @property
    def scope_id(self) -> str | None:
        return self._scope_id

    @property
    def prompt(self) -> str:
        return f"{self._path}> "

    def cd(self, target: str) -> str:
        """Change directory. Returns the new path.

        Supports:
          - Absolute paths:  /Company/Reports
          - Relative names:  Reports
          - Parent:          ..
          - Root:            /
          - Scope IDs:       scope_abc123
        """
        if target == "/":
            self._path = "/"
            self._scope_id = None
            return self._path

        if target == "..":
            if self._path == "/":
                return self._path
            parts = self._path.rstrip("/").rsplit("/", 1)
            parent = parts[0] if parts[0] else "/"
            if parent == "/":
                self._path = "/"
                self._scope_id = None
            else:
                info = unique_sdk.Folder.get_info(
                    user_id=self.config.user_id,
                    company_id=self.config.company_id,
                    folderPath=parent,
                )
                self._path = parent
                self._scope_id = info["id"]
            return self._path

        if target.startswith("scope_"):
            info = unique_sdk.Folder.get_info(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                scopeId=target,
            )
            path_resp = unique_sdk.Folder.get_folder_path(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                scope_id=target,
            )
            self._scope_id = info["id"]
            self._path = path_resp["folderPath"]
            return self._path

        if target.startswith("/"):
            resolved_path = target
        else:
            resolved_path = f"{self._path.rstrip('/')}/{target}"

        info = unique_sdk.Folder.get_info(
            user_id=self.config.user_id,
            company_id=self.config.company_id,
            folderPath=resolved_path,
        )
        self._scope_id = info["id"]
        self._path = resolved_path
        return self._path

    def resolve_path(self, target: str | None) -> tuple[str, str | None]:
        """Resolve a target to (path, scope_id) without changing state.

        Returns the current directory if target is None.
        """
        if target is None:
            return self._path, self._scope_id

        if target == "/":
            return "/", None

        if target.startswith("scope_"):
            path_resp = unique_sdk.Folder.get_folder_path(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                scope_id=target,
            )
            return path_resp["folderPath"], target

        if target.startswith("/"):
            resolved_path = target
        else:
            resolved_path = f"{self._path.rstrip('/')}/{target}"

        info = unique_sdk.Folder.get_info(
            user_id=self.config.user_id,
            company_id=self.config.company_id,
            folderPath=resolved_path,
        )
        return resolved_path, info["id"]
