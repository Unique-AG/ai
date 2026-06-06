"""UniqueQL helpers for KB ``folderId`` / ``metadata_filter`` scoping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from unique_toolkit.content.smart_rules import (
    Operator,
    Statement,
    UniqueQL,
    uniqueql_to_dict,
)

_UQL_AND = "and"


def build_folder_id_in_clause(scope_ids: list[str]) -> dict[str, Any]:
    """UniqueQL for selected folders using ``folderId in [scope_ids]``.

    Equivalent to passing ``scope_ids`` directly to the wire-level search API.
    """
    if not scope_ids:
        raise ValueError("scope_ids must be a non-empty list")
    return Statement(
        operator=Operator.IN,
        path=["folderId"],
        value=scope_ids,
    ).model_dump(mode="json")


def merge_scope_clause_into_metadata_filter(
    scope_clause: Mapping[str, Any],
    metadata_filter: UniqueQL | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """AND-merge *scope_clause* with *metadata_filter*, flattening a top-level ``and``."""
    scope_dict = dict(scope_clause)
    metadata_dict = uniqueql_to_dict(metadata_filter)
    if not metadata_dict:
        return scope_dict
    inner_and = metadata_dict.get(_UQL_AND)
    if isinstance(inner_and, list):
        return {_UQL_AND: [scope_dict, *inner_and]}
    return {_UQL_AND: [scope_dict, metadata_dict]}


__all__ = [
    "build_folder_id_in_clause",
    "merge_scope_clause_into_metadata_filter",
]
