"""Set assistant space ingestion settings from a config file."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

import typer
import yaml
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.payload_files import load_json_or_yaml_mapping


def cmd_space_ingestion_set(
    cfg: Config,
    *,
    space_id: str,
    config_path: Path,
    dry_run: bool,
) -> None:
    try:
        ingestion = load_json_or_yaml_mapping(config_path)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in config file: {exc}", err=True)
        sys.exit(2)
    except yaml.YAMLError as exc:
        typer.echo(f"Invalid YAML in config file: {exc}", err=True)
        sys.exit(2)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    try:
        current = Space.get_space(cfg.user_id, cfg.company_id, space_id)
    except Exception as exc:
        typer.echo(f"get_space failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space ingestion get_space"
        )
        sys.exit(1)

    raw_settings = current.get("settings")
    base: dict[str, Any]
    if isinstance(raw_settings, dict):
        base = dict(raw_settings)
    else:
        base = {}
    new_settings = {**base, "ingestionConfig": ingestion}

    if dry_run:
        keys = sorted(new_settings.keys())
        typer.echo(f"Dry-run: would patch settings keys on {space_id!r}: {keys!r}.")
        return

    try:
        Space.update_space(
            cfg.user_id,
            cfg.company_id,
            space_id,
            settings=cast("dict[str, Any]", new_settings),
        )
    except Exception as exc:
        typer.echo(f"update_space failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="space ingestion set")
        sys.exit(1)

    typer.echo(f"Updated settings.ingestionConfig on space {space_id!r}.")
