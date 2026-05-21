"""Grant group access on knowledge-base folders."""

from __future__ import annotations

import sys
from typing import Any, Literal, cast

import typer
from unique_sdk import Folder
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure

FolderPerm = Literal["READ", "WRITE"]


def cmd_access_grant(
    cfg: Config,
    *,
    folder_path: str | None,
    scope_id: str | None,
    group_ids: tuple[str, ...],
    permission: FolderPerm,
    apply_to_subfolders: bool,
) -> None:
    if bool(folder_path) == bool(scope_id):
        typer.echo(
            "Specify exactly one of --folder-path or --scope-id.",
            err=True,
        )
        sys.exit(2)
    if not group_ids:
        typer.echo("Provide at least one --group.", err=True)
        sys.exit(2)

    accesses = [
        {
            "entityId": gid,
            "entityType": "GROUP",
            "type": permission,
        }
        for gid in group_ids
    ]
    payload: dict[str, Any] = {
        "scopeAccesses": accesses,
        "applyToSubScopes": apply_to_subfolders,
    }
    if scope_id:
        payload["scopeId"] = scope_id
    else:
        payload["folderPath"] = folder_path

    try:
        Folder.add_access(
            cfg.user_id,
            cfg.company_id,
            **cast(Any, payload),
        )
    except Exception as exc:
        typer.echo(f"add_access failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="kb access grant")
        sys.exit(1)

    typer.echo(
        f"Granted {permission} to {len(group_ids)} group(s)"
        + (
            " (including subfolders)."
            if apply_to_subfolders
            else " (this folder only)."
        )
    )
