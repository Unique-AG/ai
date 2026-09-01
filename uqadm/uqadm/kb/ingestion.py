"""Read and apply ingestion configuration on knowledge-base folders."""

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
from uqadm.core.config_output import write_config_document
from uqadm.core.model_refs import to_plain_object
from uqadm.core.payload_files import load_json_or_yaml_mapping


def _folder_selector(folder_path: str | None, scope_id: str | None) -> dict[str, Any]:
    """Return the API's folder-target params, requiring exactly one selector."""
    if bool(folder_path) == bool(scope_id):
        typer.echo(
            "Specify exactly one of --folder-path or --scope-id.",
            err=True,
        )
        sys.exit(2)
    if scope_id:
        return {"scopeId": scope_id}
    return {"folderPath": folder_path}


def cmd_ingestion_get(
    cfg: Config,
    *,
    folder_path: str | None,
    scope_id: str | None,
    output: Path | None,
) -> None:
    selector = _folder_selector(folder_path, scope_id)

    try:
        info = Folder.get_info(cfg.user_id, cfg.company_id, **cast(Any, selector))
    except Exception as exc:
        typer.echo(f"get_info failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="kb ingestion get")
        sys.exit(1)

    ingestion_config = to_plain_object(info.get("ingestionConfig"))
    if not ingestion_config:
        typer.echo(
            "Folder has no ingestion config set; emitting an empty mapping.",
            err=True,
        )

    write_config_document(ingestion_config, output)
    if output is not None:
        typer.echo(f"Wrote ingestion config to {output}.", err=True)


def cmd_ingestion_set(
    cfg: Config,
    *,
    config_path: Path,
    folder_path: str | None,
    scope_id: str | None,
    apply_to_subfolders: bool,
) -> None:
    selector = _folder_selector(folder_path, scope_id)

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
        **selector,
    }

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
