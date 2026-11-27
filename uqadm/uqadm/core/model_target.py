"""Resolve the replacement model from the ``--to-model`` value.

``--to-model`` takes either a model name or a path to a JSON/YAML file holding
language-model info. A name is written at matched sites as a plain string; a
file is written as the full mapping it contains.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from uqadm.core.payload_files import load_json_or_yaml_mapping

_FILE_SUFFIXES = (".json", ".yaml", ".yml")


class ModelTargetError(ValueError):
    """Invalid ``--to-model`` value or model-info file contents."""


@dataclass(frozen=True)
class ModelTarget:
    """Resolved replacement model.

    ``value`` is written at every matched site: the name string when a name was
    given, or the full model-info mapping when a file was given.
    """

    name: str
    value: str | dict[str, Any]


def _looks_like_path(raw: str) -> bool:
    """True when ``raw`` is shaped like a file path rather than a model name."""
    if Path(raw).suffix.lower() in _FILE_SUFFIXES:
        return True
    return os.sep in raw or (os.altsep is not None and os.altsep in raw)


def resolve_model_target(to_model: str) -> ModelTarget:
    """Build a :class:`ModelTarget` from the ``--to-model`` value.

    An existing ``.json`` / ``.yaml`` / ``.yml`` file is loaded and used whole;
    anything else is taken as a model name. A value shaped like a path that
    does not resolve to a file is rejected rather than silently treated as a
    model name, so a mistyped path cannot be written into every config.
    """
    if not to_model.strip():
        raise ModelTargetError(
            "--to-model must be a non-empty model name or file path."
        )

    path = Path(to_model).expanduser()
    if not path.is_file():
        if _looks_like_path(to_model):
            raise ModelTargetError(
                f"--to-model {to_model!r} looks like a file path, but no such file "
                "exists. Pass a readable .json/.yaml/.yml file, or a bare model name."
            )
        return ModelTarget(name=to_model, value=to_model)

    try:
        info = load_json_or_yaml_mapping(path)
    except json.JSONDecodeError as exc:
        raise ModelTargetError(f"Invalid JSON in {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ModelTargetError(f"Invalid YAML in {path}: {exc}") from exc
    except ValueError as exc:
        raise ModelTargetError(f"{path}: {exc}") from exc

    name = info.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ModelTargetError(
            f"{path}: model info must include a non-empty string 'name'."
        )
    return ModelTarget(name=name, value=info)
