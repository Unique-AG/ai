"""UniqueQL helpers for folding KB ``scope_ids`` into ``metadata_filter``.

Uses string operators/combinators compatible with :mod:`unique_sdk` UniqueQL
(see ``unique_sdk._unique_ql``) without importing ``unique_sdk`` from callers
that must stay import-linter clean.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any, cast

_UQL_AND = "and"


def build_folder_id_scope_clause(scope_ids: list[str]) -> dict[str, Any]:
    """UniqueQL: ``folderId`` in the given scope id list (OR of folders)."""
    return {
        "path": ["folderId"],
        "operator": "in",
        "value": list(scope_ids),  # better safe than sorry
    }


def merge_scope_clause_into_metadata_filter(
    scope_clause: Mapping[str, Any],
    metadata_filter: dict[str, Any] | None,
) -> dict[str, Any]:
    """AND-merge *scope_clause* with *metadata_filter*, flattening a top-level ``and``."""
    scope_dict = dict(scope_clause)
    if not metadata_filter:
        return scope_dict
    inner_and = metadata_filter.get(_UQL_AND)
    if isinstance(inner_and, list):
        return {_UQL_AND: [scope_dict, *inner_and]}
    return {_UQL_AND: [scope_dict, dict(metadata_filter)]}


def merge_deprecated_scope_ids_into_filter(
    scope_ids: list[str] | None,
    metadata_filter: dict[str, Any] | None,
    *,
    deprecation_message: str,
    stacklevel: int = 2,
) -> dict[str, Any] | None:
    """Fold non-empty *scope_ids* into *metadata_filter*; emit ``DeprecationWarning``."""
    if not scope_ids:
        return metadata_filter
    warnings.warn(
        deprecation_message,
        DeprecationWarning,
        stacklevel=stacklevel,
    )
    clause = build_folder_id_scope_clause(scope_ids)
    return merge_scope_clause_into_metadata_filter(clause, metadata_filter)


def fold_deprecated_scope_ids_in_config_data(data: dict[str, Any]) -> dict[str, Any]:
    """``model_validator(mode='before')`` body for KB internal search config."""
    scope_raw = data.get("scope_ids")
    if scope_raw is None and "scopeIds" in data:
        scope_raw = data.get("scopeIds")
    if not scope_raw:
        return data

    meta = data.get("metadata_filter")
    if meta is None and "metadataFilter" in data:
        meta = data.get("metadataFilter")
    meta_dict = cast("dict[str, Any] | None", meta if isinstance(meta, dict) else None)

    merged = merge_deprecated_scope_ids_into_filter(
        list(scope_raw),
        meta_dict,
        deprecation_message=(
            "KnowledgeBaseInternalSearchConfig.scope_ids is deprecated; "
            "use metadata_filter (e.g. folderId with operator 'in') instead."
        ),
        stacklevel=3,
    )
    out = dict(data)
    out["scope_ids"] = None
    out.pop("scopeIds", None)
    out["metadata_filter"] = merged
    if "metadataFilter" in out:
        out["metadataFilter"] = merged
    return out


__all__ = [
    "build_folder_id_scope_clause",
    "fold_deprecated_scope_ids_in_config_data",
    "merge_deprecated_scope_ids_into_filter",
    "merge_scope_clause_into_metadata_filter",
]
