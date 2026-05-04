"""UniqueQL helpers for KB ``folderIdPath`` / ``metadata_filter`` scoping."""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

from unique_toolkit.content.smart_rules import Operator, OrStatement, Statement

_UQL_AND = "and"

# Shared with ``KnowledgeBaseService`` wire-format folder paths (folderIdPath ``contains``).
FOLDER_ID_PATH_VALUE_PREFIX = "uniquepathid://"


def _validate_folder_id_path_values(folder_id_paths: list[str]) -> None:
    if not folder_id_paths:
        raise ValueError("folder_id_paths must be a non-empty list")
    prefix = FOLDER_ID_PATH_VALUE_PREFIX
    for raw in folder_id_paths:
        if not isinstance(raw, str):
            raise TypeError(
                f"each folderIdPath value must be a str, got {type(raw).__name__}"
            )
        if not raw:
            raise ValueError("each folderIdPath value must be a non-empty str")
        if not raw.startswith(prefix):
            raise ValueError(
                f"folderIdPath value must start with {prefix!r} "
                f"(root-to-leaf scope id path), got {raw!r}"
            )
        rest = raw[len(prefix) :]
        segments = [s for s in rest.split("/") if s]
        if not segments:
            raise ValueError(
                "folderIdPath value must include at least one scope id segment "
                f"after the prefix, got {raw!r}"
            )


def build_folder_id_path_scope_clause(folder_id_paths: list[str]) -> dict[str, Any]:
    """UniqueQL for selected folders using UI-style ``folderIdPath contains`` rules."""
    _validate_folder_id_path_values(folder_id_paths)
    clauses = [
        Statement(
            operator=Operator.CONTAINS,
            path=["folderIdPath"],
            value=folder_id_path,
        )
        for folder_id_path in folder_id_paths
    ]
    if len(clauses) == 1:
        return clauses[0].model_dump(mode="json")
    return OrStatement(or_list=clauses).model_dump(mode="json")


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
    """Merge **already-resolved** ``uniquepathid://`` paths for legacy call sites; warns."""
    if not scope_ids:
        return metadata_filter
    warnings.warn(
        deprecation_message,
        DeprecationWarning,
        stacklevel=stacklevel,
    )
    clause = build_folder_id_path_scope_clause(scope_ids)
    return merge_scope_clause_into_metadata_filter(clause, metadata_filter)


__all__ = [
    "build_folder_id_path_scope_clause",
    "merge_deprecated_scope_ids_into_filter",
    "merge_scope_clause_into_metadata_filter",
]
