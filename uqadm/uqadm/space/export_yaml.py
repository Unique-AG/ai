"""YAML serialization for space snapshots (prompt-friendly block scalars)."""

from __future__ import annotations

from typing import Any

import yaml


class SpaceSnapshotDumper(yaml.SafeDumper):
    """SafeDumper with string handling aligned with internal config-converter."""


def _represent_str(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    # Mirrors config-converter: turn literal \n into newlines; trim spaces before newlines.
    processed_data = data.replace("\\n", "\n")
    while " \n" in processed_data:
        processed_data = processed_data.replace(" \n", "\n")
    if "\n" in processed_data:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", processed_data, style="|"
        )
    return dumper.represent_scalar("tag:yaml.org,2002:str", processed_data)


SpaceSnapshotDumper.add_representer(str, _represent_str)


def dump_space_snapshot_yaml(normalized: dict[str, Any]) -> str:
    """Dump a JSON-normalized mapping to YAML (trailing newline not included)."""
    return yaml.dump(
        normalized,
        Dumper=SpaceSnapshotDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
        width=5000,
    )
