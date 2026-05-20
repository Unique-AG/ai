"""Apply ingestion configuration to knowledge-base folders."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

import typer
import yaml
from unique_sdk import Folder
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.payload_files import load_json_or_yaml_mapping


def cmd_ingestion_set(
    cfg: Config,
    *,
    config_path: Path,
    folder_path: str | None,
    scope_id: str | None,
    apply_to_subfolders: bool,
) -> None:
    if bool(folder_path) == bool(scope_id):
        typer.echo(
            "Specify exactly one of --folder-path or --scope-id.",
            err=True,
        )
        sys.exit(2)

    try:
        ingestion_config = load_json_or_yaml_mapping(config_path)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in config file: {exc}", err=True)
        sys.exit(2)
    except yaml.YAMLError as exc:
        typer.echo(f"Invalid YAML in config file: {exc}", err=True)
        sys.exit(2)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    payload: dict[str, Any] = {
        "ingestionConfig": ingestion_config,
        "applyToSubScopes": apply_to_subfolders,
    }
    if scope_id:
        payload["scopeId"] = scope_id
    else:
        payload["folderPath"] = folder_path

    try:
        Folder.update_ingestion_config(
            cfg.user_id,
            cfg.company_id,
            **cast(Any, payload),
        )
    except Exception as exc:
        typer.echo(f"update_ingestion_config failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="kb ingestion set")
        sys.exit(1)

    typer.echo(
        "Ingestion config updated"
        + (
            " (including subfolders)."
            if apply_to_subfolders
            else " (this folder only)."
        )
    )
