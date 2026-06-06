"""Load JSON/YAML mapping files and newline-separated path lists."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import yaml


def snapshot_format_for_path(path: Path) -> Literal["json", "yaml"]:
    """Return file format from ``path`` suffix, or raise ``ValueError`` if invalid."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in (".yaml", ".yml"):
        return "yaml"
    raise ValueError(f"File must end with .json, .yaml, or .yml (got: {path.name!r}).")


def load_json_or_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a JSON or YAML file whose root must be a mapping."""
    fmt = snapshot_format_for_path(path)
    raw_text = path.read_text(encoding="utf-8")
    if fmt == "json":
        data = json.loads(raw_text)
    else:
        data = yaml.safe_load(raw_text)
    if not isinstance(data, dict):
        detail = type(data).__name__
        raise ValueError(f"Document root must be a mapping (got {detail}).")
    return dict(data)


def read_path_list_file(path: Path) -> list[str]:
    """Read non-empty folder paths: one per line, ``#`` starts an end-of-line comment."""
    raw_text = path.read_text(encoding="utf-8")
    result: list[str] = []
    for line in raw_text.splitlines():
        content = line.split("#", 1)[0].strip()
        if not content:
            continue
        result.append(content)
    return result
