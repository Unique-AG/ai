"""Replace language-model references in space configurations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
import yaml
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.interactive import confirm_each
from uqadm.core.model_refs import ModelRef, replace_model_refs
from uqadm.core.model_target import ModelTarget, ModelTargetError, resolve_model_target
from uqadm.core.payload_files import load_json_or_yaml_mapping
from uqadm.space.export import export_format_for_output_path
from uqadm.space.export_yaml import dump_space_snapshot_yaml
from uqadm.space.list import fetch_all_spaces

#: Top-level space fields Space.update_space can write and the rewrite may touch.
_UPDATABLE_TOP_LEVEL_KEYS = (
    "languageModel",
    "switchableLanguageModels",
    "settings",
    "subAgentSettings",
)


def build_model_update_kwargs(
    old_space: dict[str, Any],
    new_space: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Build a minimal ``update_space`` payload from the rewritten space.

    Only fields that actually changed are included: supported top-level keys
    plus per-module ``{"moduleId", "configuration"}`` entries. Changed fields
    that ``update_space`` cannot write are returned separately so callers can
    warn about them.
    """
    kwargs: dict[str, Any] = {}
    unsupported: list[str] = []
    for key in new_space:
        if key == "modules":
            continue
        if old_space.get(key) == new_space.get(key):
            continue
        if key in _UPDATABLE_TOP_LEVEL_KEYS:
            kwargs[key] = new_space[key]
        else:
            unsupported.append(key)

    module_updates: list[dict[str, Any]] = []
    old_modules = list(old_space.get("modules") or [])
    new_modules = list(new_space.get("modules") or [])
    for index, (old_module, new_module) in enumerate(zip(old_modules, new_modules)):
        if old_module.get("configuration") == new_module.get("configuration"):
            continue
        module_id = new_module.get("id")
        if module_id is None:
            unsupported.append(f"modules[{index}] (missing module id)")
            continue
        module_updates.append(
            {"moduleId": module_id, "configuration": new_module["configuration"]}
        )
    if module_updates:
        kwargs["modules"] = module_updates
    return kwargs, unsupported


def _echo_refs(refs: list[ModelRef], *, err: bool = False) -> None:
    for ref in refs:
        typer.echo(f"  {ref.path}", err=err)


def _warn_unsupported(unsupported: list[str]) -> None:
    if unsupported:
        typer.echo(
            "Warning: matches under field(s) not writable via Space.update_space "
            "were NOT applied: " + ", ".join(sorted(unsupported)),
            err=True,
        )


def _write_snapshot(snapshot: dict[str, Any], output: Path | None) -> None:
    normalized: dict[str, Any] = json.loads(
        json.dumps(snapshot, sort_keys=True, default=str)
    )
    if output is None:
        typer.echo(json.dumps(normalized, indent=2, sort_keys=True))
        return
    try:
        fmt = export_format_for_output_path(output)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)
    if fmt == "json":
        text = json.dumps(normalized, indent=2, sort_keys=True)
    else:
        text = dump_space_snapshot_yaml(normalized).rstrip("\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + "\n", encoding="utf-8")


def _fetch_space(cfg: Config, space_id: str) -> dict[str, Any]:
    try:
        return Space.get_space(cfg.user_id, cfg.company_id, space_id)
    except Exception as exc:
        typer.echo(f"Error fetching space {space_id!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space model-replace get_space"
        )
        sys.exit(1)


def _apply_update(cfg: Config, space_id: str, kwargs: dict[str, Any]) -> bool:
    try:
        Space.update_space(cfg.user_id, cfg.company_id, space_id, **kwargs)
    except Exception as exc:
        typer.echo(f"update_space failed for {space_id!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space model-replace update_space"
        )
        return False
    return True


def _run_file_mode(
    file_path: Path,
    *,
    from_model: str,
    target: ModelTarget,
    output: Path | None,
    dry_run: bool,
) -> None:
    try:
        snapshot = load_json_or_yaml_mapping(file_path)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in snapshot: {exc}", err=True)
        sys.exit(2)
    except yaml.YAMLError as exc:
        typer.echo(f"Invalid YAML in snapshot: {exc}", err=True)
        sys.exit(2)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    new_snapshot, refs = replace_model_refs(snapshot, from_model, target.value)
    if not refs:
        typer.echo(f"No occurrences of {from_model!r} found in {file_path}.", err=True)
    else:
        typer.echo(
            f"{len(refs)} replacement(s) of {from_model!r} in {file_path}:", err=True
        )
        _echo_refs(refs, err=True)
    if dry_run:
        typer.echo("Dry-run: no output written.", err=True)
        return
    _write_snapshot(new_snapshot, output)
    if output is not None:
        typer.echo(f"Wrote rewritten snapshot to {output}.", err=True)


def _run_single(
    cfg: Config,
    space_id: str,
    *,
    from_model: str,
    target: ModelTarget,
    output: Path | None,
    dry_run: bool,
) -> None:
    space = _fetch_space(cfg, space_id)
    new_space, refs = replace_model_refs(space, from_model, target.value)
    label = f"{space_id} ({space.get('name', '')!r})"
    if not refs:
        typer.echo(f"No occurrences of {from_model!r} in space {label}; nothing to do.")
        return
    typer.echo(f"Space {label}: {len(refs)} match(es) for {from_model!r}:")
    _echo_refs(refs)

    if output is not None:
        _write_snapshot(new_space, output)
        typer.echo(f"Wrote rewritten snapshot to {output} (no API changes made).")
        return

    kwargs, unsupported = build_model_update_kwargs(space, new_space)
    _warn_unsupported(unsupported)
    if not kwargs:
        typer.echo("No updatable fields changed; nothing to send.", err=True)
        return
    if dry_run:
        typer.echo(
            f"Dry-run: would update_space {space_id!r} with fields "
            f"{sorted(kwargs.keys())!r}."
        )
        return
    if not _apply_update(cfg, space_id, kwargs):
        sys.exit(1)
    typer.echo(f"Updated space {space_id} ({len(refs)} model reference(s) replaced).")


def _run_sweep(
    cfg: Config,
    *,
    name_filter: str | None,
    from_model: str,
    target: ModelTarget,
    dry_run: bool,
    assume_yes: bool,
) -> None:
    try:
        rows = fetch_all_spaces(cfg.user_id, cfg.company_id, name_filter=name_filter)
    except Exception as exc:
        typer.echo(f"Error listing spaces: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space model-replace list"
        )
        sys.exit(1)

    apply_all = assume_yes
    scanned = 0
    matched = 0
    updated = 0
    failed = 0
    for row in rows:
        space_id = row.get("id")
        if not space_id:
            continue
        try:
            space = Space.get_space(cfg.user_id, cfg.company_id, space_id)
        except Exception as exc:
            typer.echo(f"Warning: skipping space {space_id!r}: {exc}", err=True)
            failed += 1
            continue
        scanned += 1
        new_space, refs = replace_model_refs(space, from_model, target.value)
        if not refs:
            continue
        matched += 1
        typer.echo(
            f"\nSpace {space_id} ({space.get('name', '')!r}): "
            f"{len(refs)} match(es) for {from_model!r}:"
        )
        _echo_refs(refs)
        kwargs, unsupported = build_model_update_kwargs(space, new_space)
        _warn_unsupported(unsupported)
        if not kwargs:
            typer.echo("No updatable fields changed; skipping.", err=True)
            continue
        if dry_run:
            typer.echo(
                f"Dry-run: would update_space {space_id!r} with fields "
                f"{sorted(kwargs.keys())!r}."
            )
            continue
        if not apply_all:
            decision = confirm_each(f"Replace model in space {space_id}?")
            if decision == "quit":
                typer.echo("Aborted by user.")
                break
            if decision == "no":
                continue
            if decision == "all":
                apply_all = True
        if _apply_update(cfg, space_id, kwargs):
            updated += 1
            typer.echo(f"Updated space {space_id}")
        else:
            failed += 1

    typer.echo(
        f"\nScanned {scanned} space(s): {matched} with matches, {updated} updated."
    )
    if failed:
        typer.echo(f"{failed} space(s) failed; see warnings above.", err=True)
        sys.exit(1)


def cmd_model_replace(
    cfg: Config | None,
    *,
    space_id: str | None,
    file_path: Path | None,
    sweep_all: bool,
    name_filter: str | None,
    from_model: str,
    to_model: str,
    output: Path | None,
    dry_run: bool,
    assume_yes: bool,
) -> None:
    """Replace ``from_model`` references in one space, a snapshot file, or all spaces."""
    mode_count = sum(
        (space_id is not None, file_path is not None, sweep_all),
    )
    if mode_count != 1:
        typer.echo("Specify exactly one of SPACE_ID, --file, or --all.", err=True)
        sys.exit(2)
    if sweep_all and output is not None:
        typer.echo("--output cannot be combined with --all.", err=True)
        sys.exit(2)

    try:
        target = resolve_model_target(to_model)
    except ModelTargetError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    if target.name == from_model:
        typer.echo(
            "Warning: --from-model and the replacement model name are identical.",
            err=True,
        )

    if file_path is not None:
        _run_file_mode(
            file_path,
            from_model=from_model,
            target=target,
            output=output,
            dry_run=dry_run,
        )
        return

    assert cfg is not None
    if space_id is not None:
        _run_single(
            cfg,
            space_id,
            from_model=from_model,
            target=target,
            output=output,
            dry_run=dry_run,
        )
        return

    _run_sweep(
        cfg,
        name_filter=name_filter,
        from_model=from_model,
        target=target,
        dry_run=dry_run,
        assume_yes=assume_yes,
    )
