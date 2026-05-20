"""Create knowledge-base folder paths."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import typer
from unique_sdk import Folder
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.payload_files import read_path_list_file


def _collect_paths(
    extra_paths: Sequence[str],
    paths_file: Path | None,
) -> list[str]:
    collected: list[str] = []
    if paths_file is not None:
        collected.extend(read_path_list_file(paths_file))
    collected.extend(extra_paths)
    seen: set[str] = set()
    unique: list[str] = []
    for p in collected:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def cmd_mkdir(
    cfg: Config,
    *,
    extra_paths: Sequence[str],
    paths_file: Path | None,
    parent_scope_id: str | None,
    inherit_access: bool,
) -> None:
    paths = _collect_paths(extra_paths, paths_file)
    if not paths:
        typer.echo(
            "Provide at least one path (--path or positional) and/or --paths-file.",
            err=True,
        )
        sys.exit(2)

    params: dict[str, Any] = {"inheritAccess": inherit_access}
    if parent_scope_id:
        params["parentScopeId"] = parent_scope_id
        params["relativePaths"] = paths
    else:
        params["paths"] = paths

    try:
        result = Folder.create_paths(
            cfg.user_id,
            cfg.company_id,
            **cast(Any, params),
        )
    except Exception as exc:
        typer.echo(f"create_paths failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="kb mkdir")
        sys.exit(1)

    created = result.get("createdFolders") or []
    if not created:
        typer.echo("No new folders reported by the API (paths may already exist).")
        return
    for folder in created:
        typer.echo(f"{folder.get('id', '?')}\t{folder.get('name', '')}")
