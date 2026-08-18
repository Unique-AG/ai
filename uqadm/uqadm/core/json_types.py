"""Recursive types for the JSON documents uqadm reads, rewrites and writes.

Space snapshots, folder ingestion configs and SDK payloads are all arbitrary
JSON. Modelling them as ``JsonValue`` rather than ``Any`` keeps type checking
alive inside the helpers that walk them: a key lookup on a value that could be
a list, or a ``.get`` on a value that could be a string, is then an error at
review time instead of a crash on someone's config.
"""

from __future__ import annotations

from typing import TypeAlias

#: Any value that survives a JSON round-trip.
JsonValue: TypeAlias = (
    "str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]"
)

#: A JSON object: the root of every document uqadm loads.
JsonObject: TypeAlias = "dict[str, JsonValue]"
