"""Resolve the workspace root that per-turn ``.unique/`` manifests belong to.

The platform reads manifests back against a fixed root, and the agent moves
the shell's directory with ``cd``. Manifest paths anchor here; user-facing
output paths MUST NEVER, so ``cd out && unique-cli download X`` still lands
in ``out``.
"""

from __future__ import annotations

import os
from pathlib import Path

from unique_sdk.cli.identity import TURN_IDENTITY_ENV_VAR

WORKSPACE_ENV_VAR = "UNIQUE_WORKSPACE_DIR"
UNIQUE_DIR_NAME = ".unique"


def workspace_root() -> Path:
    """Directory the ``.unique`` manifest tree hangs off. Never raises.

    ``$UNIQUE_WORKSPACE_DIR``, then the workspace holding
    ``$UNIQUE_TURN_IDENTITY_FILE``, then ``$HOME``, then the cwd. NEVER add an
    ancestor walk: a directory that once ran a turn keeps a stray
    ``sub/.unique`` that would capture every later call made from inside it.
    """
    for candidate in (
        _from_env(),
        _from_turn_identity(),
        _from_home(),
    ):
        if candidate is not None:
            return candidate
    return Path.cwd()


def unique_dir() -> Path:
    """``<workspace root>/.unique``, not created here."""
    return workspace_root() / UNIQUE_DIR_NAME


def manifest_path(relative: Path | str) -> Path:
    """Anchor a manifest path such as ``.unique/web-refs.jsonl``."""
    return workspace_root() / relative


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _from_env() -> Path | None:
    raw = os.environ.get(WORKSPACE_ENV_VAR, "").strip()
    if not raw:
        return None
    candidate = Path(raw)
    return candidate if _is_dir(candidate) else None


def _from_turn_identity() -> Path | None:
    raw = os.environ.get(TURN_IDENTITY_ENV_VAR, "").strip()
    if not raw:
        return None
    identity = Path(raw)
    if identity.parent.name != UNIQUE_DIR_NAME:
        return None
    root = identity.parent.parent
    return root if _is_dir(root) else None


def _from_home() -> Path | None:
    raw = os.environ.get("HOME", "").strip()
    if not raw:
        return None
    home = Path(raw)
    return home if _is_dir(home / UNIQUE_DIR_NAME) else None
