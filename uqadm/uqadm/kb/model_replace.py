"""Replace language-model references in KB folder ingestion configs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterator, cast

import typer
import yaml
from unique_sdk import Folder
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.config_output import write_config_document
from uqadm.core.interactive import confirm_each
from uqadm.core.model_refs import (
    MISSING,
    ModelRef,
    get_at_path,
    replace_model_refs,
    to_plain,
    value_matches,
)
from uqadm.core.model_target import ModelTarget, ModelTargetError, resolve_model_target
from uqadm.core.payload_files import load_json_or_yaml_mapping

_PAGE_SIZE = 100


def _echo_refs(refs: list[ModelRef], *, err: bool = False) -> None:
    for ref in refs:
        typer.echo(f"  {ref.path}", err=err)


def verify_replacements(
    config: dict[str, Any],
    refs: list[ModelRef],
    from_model: str,
) -> list[str]:
    """Check that every rewritten path landed in the re-read ``config``.

    Current platforms accept and return the full ingestion config, but older
    ones validated the write against a restricted DTO and stripped the rest on
    read, so a rewritten key could vanish without an error. Verifying the
    re-read keeps that failure visible instead of silent.
    Returns a failure description per reference that did not land.
    """
    failures: list[str] = []
    for ref in refs:
        value = get_at_path(config, ref.path)
        if value is MISSING:
            failures.append(f"{ref.path}: key missing after update (dropped by API)")
        elif value_matches(value, from_model):
            failures.append(f"{ref.path}: still set to {from_model!r}")
    return failures


def _get_folder_info(
    cfg: Config,
    *,
    folder_path: str | None,
    scope_id: str | None,
) -> Folder.FolderInfo:
    params: dict[str, Any] = {}
    if scope_id:
        params["scopeId"] = scope_id
    else:
        params["folderPath"] = folder_path
    try:
        return Folder.get_info(cfg.user_id, cfg.company_id, **cast(Any, params))
    except Exception as exc:
        typer.echo(f"Error fetching folder info: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="kb ingestion model-replace get_info"
        )
        sys.exit(1)


def _folder_label(cfg: Config, info: Folder.FolderInfo) -> str:
    scope_id = info["id"]
    try:
        path = Folder.get_folder_path(cfg.user_id, cfg.company_id, scope_id)[
            "folderPath"
        ]
        return f"{path} ({scope_id})"
    except Exception:
        return f"{info.get('name', '?')} ({scope_id})"


def _update_and_verify(
    cfg: Config,
    scope_id: str,
    new_config: dict[str, Any],
    refs: list[ModelRef],
    from_model: str,
    *,
    apply_to_subfolders: bool,
) -> list[str]:
    """PATCH the ingestion config, re-read it, and return verification failures."""
    try:
        Folder.update_ingestion_config(
            cfg.user_id,
            cfg.company_id,
            **cast(
                Any,
                {
                    "scopeId": scope_id,
                    "ingestionConfig": new_config,
                    "applyToSubScopes": apply_to_subfolders,
                },
            ),
        )
    except Exception as exc:
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="kb ingestion model-replace update_ingestion_config"
        )
        return [f"update_ingestion_config failed: {exc}"]

    try:
        reread = Folder.get_info(
            cfg.user_id, cfg.company_id, **cast(Any, {"scopeId": scope_id})
        )
    except Exception as exc:
        return [f"could not re-read folder for verification: {exc}"]
    return verify_replacements(
        to_plain(reread.get("ingestionConfig") or {}), refs, from_model
    )


def _iter_folders(cfg: Config) -> Iterator[Folder.FolderInfo]:
    """Yield every folder in the tenant, walking the tree from the root."""
    stack: list[str | None] = [None]
    while stack:
        parent_id = stack.pop()
        skip = 0
        while True:
            params: dict[str, Any] = {"skip": skip, "take": _PAGE_SIZE}
            if parent_id is not None:
                params["parentId"] = parent_id
            page = Folder.get_infos(cfg.user_id, cfg.company_id, **cast(Any, params))
            batch = list(page.get("folderInfos") or [])
            for info in batch:
                yield info
                stack.append(info["id"])
            if len(batch) < _PAGE_SIZE:
                break
            skip += _PAGE_SIZE


def _run_file_mode(
    file_path: Path,
    *,
    from_model: str,
    target: ModelTarget,
    output: Path | None,
    dry_run: bool,
) -> None:
    try:
        config = load_json_or_yaml_mapping(file_path)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in config file: {exc}", err=True)
        sys.exit(2)
    except yaml.YAMLError as exc:
        typer.echo(f"Invalid YAML in config file: {exc}", err=True)
        sys.exit(2)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    new_config, refs = replace_model_refs(config, from_model, target.value)
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
    write_config_document(new_config, output)
    if output is not None:
        typer.echo(f"Wrote rewritten ingestion config to {output}.", err=True)


def _run_single(
    cfg: Config,
    *,
    folder_path: str | None,
    scope_id: str | None,
    from_model: str,
    target: ModelTarget,
    output: Path | None,
    apply_to_subfolders: bool,
    dry_run: bool,
) -> None:
    info = _get_folder_info(cfg, folder_path=folder_path, scope_id=scope_id)
    config = to_plain(info.get("ingestionConfig") or {})
    new_config, refs = replace_model_refs(config, from_model, target.value)
    label = _folder_label(cfg, info)
    if not refs:
        typer.echo(
            f"No occurrences of {from_model!r} in folder {label}; nothing to do."
        )
        return
    typer.echo(f"Folder {label}: {len(refs)} match(es) for {from_model!r}:")
    _echo_refs(refs)

    if output is not None:
        write_config_document(new_config, output)
        typer.echo(f"Wrote rewritten ingestion config to {output} (no API changes).")
        return
    if dry_run:
        typer.echo(
            f"Dry-run: would update ingestion config of {label}"
            + (" (including subfolders)." if apply_to_subfolders else ".")
        )
        return

    failures = _update_and_verify(
        cfg,
        info["id"],
        new_config,
        refs,
        from_model,
        apply_to_subfolders=apply_to_subfolders,
    )
    if failures:
        typer.echo(f"Verification FAILED for folder {label}:", err=True)
        for failure in failures:
            typer.echo(f"  {failure}", err=True)
        sys.exit(1)
    typer.echo(
        f"Updated folder {label} ({len(refs)} model reference(s) replaced, verified)."
    )


def _run_sweep(
    cfg: Config,
    *,
    from_model: str,
    target: ModelTarget,
    dry_run: bool,
    assume_yes: bool,
) -> None:
    apply_all = assume_yes
    scanned = 0
    matched = 0
    updated = 0
    failed = 0
    try:
        for info in _iter_folders(cfg):
            scanned += 1
            config = to_plain(info.get("ingestionConfig") or {})
            new_config, refs = replace_model_refs(config, from_model, target.value)
            if not refs:
                continue
            matched += 1
            label = _folder_label(cfg, info)
            typer.echo(f"\nFolder {label}: {len(refs)} match(es) for {from_model!r}:")
            _echo_refs(refs)
            if dry_run:
                typer.echo(f"Dry-run: would update ingestion config of {label}.")
                continue
            if not apply_all:
                decision = confirm_each(f"Replace model in folder {label}?")
                if decision == "quit":
                    typer.echo("Aborted by user.")
                    break
                if decision == "no":
                    continue
                if decision == "all":
                    apply_all = True
            failures = _update_and_verify(
                cfg,
                info["id"],
                new_config,
                refs,
                from_model,
                apply_to_subfolders=False,
            )
            if failures:
                failed += 1
                typer.echo(f"Verification FAILED for folder {label}:", err=True)
                for failure in failures:
                    typer.echo(f"  {failure}", err=True)
            else:
                updated += 1
                typer.echo(f"Updated folder {label}")
    except Exception as exc:
        typer.echo(f"Error walking KB folders: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="kb ingestion model-replace get_infos"
        )
        sys.exit(1)

    typer.echo(
        f"\nScanned {scanned} folder(s): {matched} with matches, {updated} updated."
    )
    if failed:
        typer.echo(f"{failed} folder(s) failed; see warnings above.", err=True)
        sys.exit(1)


def cmd_model_replace(
    cfg: Config | None,
    *,
    folder_path: str | None,
    scope_id: str | None,
    file_path: Path | None,
    sweep_all: bool,
    from_model: str,
    to_model: str,
    output: Path | None,
    apply_to_subfolders: bool,
    dry_run: bool,
    assume_yes: bool,
) -> None:
    """Replace ``from_model`` in a folder ingestion config, a file, or all folders."""
    if folder_path and scope_id:
        typer.echo(
            "Specify at most one of --folder-path or --scope-id.",
            err=True,
        )
        sys.exit(2)
    has_folder_target = bool(folder_path) or bool(scope_id)
    mode_count = sum((has_folder_target, file_path is not None, sweep_all))
    if mode_count != 1:
        typer.echo(
            "Specify exactly one of --folder-path/--scope-id, --file, or --all.",
            err=True,
        )
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
    if has_folder_target:
        _run_single(
            cfg,
            folder_path=folder_path,
            scope_id=scope_id,
            from_model=from_model,
            target=target,
            output=output,
            apply_to_subfolders=apply_to_subfolders,
            dry_run=dry_run,
        )
        return

    _run_sweep(
        cfg,
        from_model=from_model,
        target=target,
        dry_run=dry_run,
        assume_yes=assume_yes,
    )
