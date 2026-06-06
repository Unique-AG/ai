"""Grant user or group access to an assistant space."""

from __future__ import annotations

import sys
from typing import Literal, cast

import typer
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure

SpaceAccessType = Literal["USE", "MANAGE", "UPLOAD"]


def cmd_space_access_grant(
    cfg: Config,
    *,
    space_id: str,
    group_ids: tuple[str, ...],
    user_ids: tuple[str, ...],
    access_type: SpaceAccessType,
) -> None:
    if not group_ids and not user_ids:
        typer.echo("Provide at least one --group and/or --user.", err=True)
        sys.exit(2)

    access = cast(
        "list[Space.AccessEntry]",
        [
            *(
                {
                    "entityId": gid,
                    "entityType": "GROUP",
                    "type": access_type,
                }
                for gid in group_ids
            ),
            *(
                {
                    "entityId": uid,
                    "entityType": "USER",
                    "type": access_type,
                }
                for uid in user_ids
            ),
        ],
    )

    try:
        Space.add_space_access(
            cfg.user_id,
            cfg.company_id,
            space_id,
            access=access,
        )
    except Exception as exc:
        typer.echo(f"add_space_access failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="space access grant")
        sys.exit(1)

    typer.echo(
        f"Added {len(access)} access entr(y/ies) ({access_type}) "
        "(merged with existing ACL on the server)."
    )
