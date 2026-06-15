"""Per-message UniqueQL ``metaDataFilter`` evaluation for the CLI scope gate.

The Swappable Intelligence runner writes a per-message UniqueQL scope (e.g. an
Agentic Table column's ``scope_rules``) to ``.unique-search.json``. It can
express scopes a flat ``scopeIds`` list cannot — recursive folder CONTAINS,
contentId IN, boolean trees — and takes precedence over the static ``scopeIds``
for this turn. See UN-21780.

This module isolates the *boolean-tree logic* (walking ``and``/``or`` nodes and
the two scope-boundary leaf types) from ``ShellState``. The only external
inputs it needs — resolving a folder scope id to its path and a content id to
its owning folder path — are injected as callables, so this module stays free
of ``unique_sdk``/config/caching concerns. Those (and the API calls they wrap)
live on ``ShellState``, which owns the per-turn resolution caches.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any

# A Unique folder scope id, e.g. ``scope_ch5tigpwhamry2dqimxl3a7a``. Used to
# extract the target folder from a ``folderIdPath`` filter value, which is
# either a bare ``scope_…`` or a ``uniquepathid://scope_root/scope_leaf`` path
# (segments are ``/``-separated, so matching is bounded by the path separator).
_SCOPE_ID_RE = re.compile(r"scope_[a-z0-9_]+", re.IGNORECASE)

# UniqueQL exclusion operators whose match must be *inverted* (membership
# denies rather than grants). Enumerated explicitly rather than matched by a
# ``startswith("not")`` heuristic: that heuristic would also catch a future
# ``notEmpty``-style operator and invert it wrongly. Mirrors the Operator enum
# in unique_toolkit.content.smart_rules. See UN-21780.
_NEGATED_OPERATORS = frozenset({"notequals", "notin", "notcontains"})

ScopePathResolver = Callable[[str], "str | None"]
ContentOwnerPathResolver = Callable[[str], "str | None"]


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
    """True for exclusion operators (notIn, notEquals, notContains)."""
    return isinstance(operator, str) and operator.lower() in _NEGATED_OPERATORS


def _is_folder_only_subtree(node: Any) -> bool:
    """True if *node* grants access purely via positive ``folderIdPath`` leaves.

    Used to decide whether the folder branches of an ``or`` are navigable: an
    OR every branch of which is a folder grant means "under folder X or folder
    Y", so each folder is fully browsable. If any branch adds a ``contentId``
    allowlist (or a negated/other constraint), the folder branches are
    *conditional* and must not be treated as standalone browsable folders.
    """
    if not isinstance(node, dict):
        return False
    for key in ("and", "or"):
        if key in node:
            children = node.get(key) or []
            return bool(children) and all(_is_folder_only_subtree(c) for c in children)
    if _is_negated_operator(node.get("operator")):
        return False
    path = node.get("path")
    field = path[0] if isinstance(path, list) and path else path
    return field == "folderIdPath"


def _collect_navigable_folder_ids(
    node: Any, folder_ids: list[str] | None = None
) -> list[str]:
    """Folder scope ids the filter grants for *navigation* (ls/cd into).

    A folder is navigable only when it sits on the filter's conjunctive spine
    — reached through ``and`` nodes, or inside an ``or`` whose every branch is
    a folder grant. A folder that appears only as an ``or`` alternative to a
    ``contentId`` allowlist (e.g. ``and(folderA, or(folderB, contentId in …))``)
    is *not* navigable on its own: only specific documents under it are in
    scope, so listing/entering it would leak out-of-scope folder inventory.
    Negated leaves are exclusions and never grant navigation. See UN-21780.
    """
    if folder_ids is None:
        folder_ids = []
    if not isinstance(node, dict):
        return folder_ids
    if "and" in node:
        for child in node.get("and") or []:
            _collect_navigable_folder_ids(child, folder_ids)
        return folder_ids
    if "or" in node:
        children = node.get("or") or []
        # Only collect the OR's folders when no branch is conditional on a
        # contentId allowlist (or other non-folder constraint).
        if children and all(_is_folder_only_subtree(c) for c in children):
            for child in children:
                _collect_navigable_folder_ids(child, folder_ids)
        return folder_ids
    if _is_negated_operator(node.get("operator")):
        return folder_ids
    path = node.get("path")
    field = path[0] if isinstance(path, list) and path else path
    if field == "folderIdPath":
        value = node.get("value")
        values = value if isinstance(value, list) else [value]
        for v in values:
            scope_id = _extract_target_scope_id(v)
            if scope_id and scope_id not in folder_ids:
                folder_ids.append(scope_id)
    return folder_ids


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


class MetadataFilter:
    """A per-message UniqueQL ``metaDataFilter`` tree plus the logic to evaluate it.

    Construct with the raw filter ``tree`` (a non-empty UniqueQL dict) and two
    resolver callables that turn ids into folder paths. The class never calls
    the API directly — that, and the per-turn caching of these resolutions,
    belong to ``ShellState`` and are injected here so the boolean-tree logic
    stays pure and independently testable.

    The client enforces a *conservative subset* of UniqueQL: the two
    scope-boundary leaf types ``contentId`` (membership, free) and
    ``folderIdPath`` (containment, resolves the document's owning folder). It is
    **not** a full UniqueQL engine — any other leaf (``mimeType``, custom
    metadata keys, dates, …) cannot be evaluated from the available content
    metadata and is treated as *not satisfied* (fails closed). This guarantees
    the local gate is never broader than the intended scope; the search server
    still enforces the full filter for KB search. See UN-21780.
    """

    def __init__(
        self,
        tree: dict[str, Any],
        *,
        resolve_scope_path: ScopePathResolver,
        resolve_content_owner_path: ContentOwnerPathResolver,
    ) -> None:
        self._tree = tree
        self._resolve_scope_path = resolve_scope_path
        self._resolve_content_owner_path = resolve_content_owner_path
        # Per-content verdict cache: an OR/contentId check is cheap, but a
        # folderIdPath leaf resolves the document's owning folder, so memoise
        # the final verdict per content id for the filter's lifetime.
        self._verdict_cache: dict[str, bool] = {}

    @property
    def tree(self) -> dict[str, Any]:
        return self._tree

    # ── Content gating ─────────────────────────────────────────────────────

    def allows_content(self, content_id: str) -> bool:
        """True if *content_id* satisfies the filter (cached per content id)."""
        if content_id in self._verdict_cache:
            return self._verdict_cache[content_id]
        verdict = self._eval_node(self._tree, content_id)
        self._verdict_cache[content_id] = verdict
        return verdict

    def _eval_node(self, node: Any, content_id: str) -> bool:
        # A malformed (non-dict) node can't be proven to place the document in
        # scope, so it fails closed (deny) — consistent with unevaluable
        # leaves. Returning True here would open read/cite/download on a
        # partial or corrupt filter tree. See UN-21780.
        if not isinstance(node, dict):
            return False
        if "and" in node:
            children = node.get("and") or []
            if not children:
                # An empty `and` is a malformed group, not "no constraint".
                # Fail closed.
                return False
            return all(self._eval_node(c, content_id) for c in children)
        if "or" in node:
            children = node.get("or") or []
            if not children:
                # An `or` with no alternatives is satisfied by nothing. Fail
                # closed rather than open. See UN-21780.
                return False
            # Cheap contentId leaves first so an OR can short-circuit to True
            # without a folder-ancestry lookup.
            ordered = sorted(children, key=self._leaf_cost)
            return any(self._eval_node(c, content_id) for c in ordered)
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
        # Non-boundary leaf (e.g. mimeType, custom metadata, dates): the
        # client cannot evaluate it from the available content metadata, so it
        # fails closed (not satisfied) rather than fails open (return True).
        # Returning True here would let such a leaf inside an `or` widen the
        # result to every document the user can see — a scope leak. The search
        # server still enforces the full filter for KB search. See UN-21780.
        return False

    # ── Folder navigation ──────────────────────────────────────────────────

    def navigable_folder_ids(self) -> list[str]:
        """Folder scope ids the filter grants for navigation (ls/cd into).

        Excludes folders only reachable as an ``or`` alternative to a
        ``contentId`` allowlist, which are not standalone-browsable.
        """
        return _collect_navigable_folder_ids(self._tree)

    def _navigable_folder_paths(self) -> list[str]:
        return [
            p
            for p in (
                self._resolve_scope_path(sid) for sid in self.navigable_folder_ids()
            )
            if p
        ]

    def allows_folder_scope(self, scope_id: str) -> bool:
        """True if *scope_id* is inside one of the filter's navigable scopes.

        Gates explicit folder targets (e.g. ``ls <path>``) so navigation cannot
        enumerate folders outside the per-message scope.
        """
        folder_paths = self._navigable_folder_paths()
        if not folder_paths:
            return False
        target_path = self._resolve_scope_path(scope_id)
        if not target_path:
            return False
        return any(
            target_path == p or target_path.startswith(p + "/") for p in folder_paths
        )

    def allows_folder_path(self, folder_path: str) -> bool:
        """True if an absolute folder *path* lies within a navigable scope.

        Path-based counterpart to ``allows_folder_scope`` for targets without a
        scope id yet (e.g. a ``mkdir`` destination), so a ``..`` traversal can't
        create structure outside the task scope.
        """
        paths = self._navigable_folder_paths()
        if not paths:
            return False
        norm = os.path.normpath(folder_path)
        return any(norm == p or norm.startswith(p + "/") for p in paths)

    def scope(self) -> tuple[list[str], list[str]]:
        """Return ``(folder_paths, content_ids)`` referenced by the filter.

        Folder scope ids are resolved to absolute paths; content ids are
        returned verbatim. Used to *describe* the active scope to the agent
        (``ls`` at root, denial hints) without enumerating folder contents.
        """
        folder_ids, content_ids = _collect_filter_targets(self._tree)
        paths: list[str] = []
        for scope_id in folder_ids:
            resolved = self._resolve_scope_path(scope_id)
            if resolved:
                paths.append(resolved)
        return paths, content_ids
