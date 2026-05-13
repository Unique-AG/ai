"""Interactive and non-interactive creation of a slot env file."""

from __future__ import annotations

from typing import Optional

import typer

from uqadm.core.config_file import set_default_slot
from uqadm.core.paths import envs_dir


def _prompt(label: str, default: str | None = None, *, password: bool = False) -> str:
    """Prompt the user for a value, returning the typed input."""
    suffix = f" [{default}]" if default else ""
    prompt_text = f"{label}{suffix}"
    value = typer.prompt(prompt_text, default=default or "", hide_input=password)
    return value.strip()


def cmd_env_create(
    slot: str,
    *,
    force: bool,
    set_default: bool,
    non_interactive: bool,
    user_id: Optional[str],
    company_id: Optional[str],
    api_key: Optional[str],
    app_id: Optional[str],
    api_base: Optional[str],
) -> None:
    """Create a ``.{slot}.env`` file in ``~/.uqadm/envs/``."""
    dest_dir = envs_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    env_file = dest_dir / f".{slot}.env"

    if env_file.exists() and not force:
        typer.echo(
            f"Slot {slot!r} already exists at {env_file}. Use --force to overwrite.",
            err=True,
        )
        raise typer.Exit(1)

    if non_interactive:
        if not user_id or not company_id:
            typer.echo(
                "Error: --user-id and --company-id are required in non-interactive mode.",
                err=True,
            )
            raise typer.Exit(2)
        uid = user_id
        cid = company_id
        key = api_key or ""
        aid = app_id or ""
        base = api_base or ""
    else:
        typer.echo(f"Creating slot {slot!r} → {env_file}")
        typer.echo("Press Enter to leave optional fields blank.\n")
        uid = _prompt("UNIQUE_USER_ID", user_id)
        cid = _prompt("UNIQUE_COMPANY_ID", company_id)
        key = _prompt("UNIQUE_API_KEY (optional)", api_key, password=True)
        aid = _prompt("UNIQUE_APP_ID (optional)", app_id)
        base = _prompt("UNIQUE_API_BASE (optional)", api_base)

    lines = [
        f"UNIQUE_USER_ID={uid}",
        f"UNIQUE_COMPANY_ID={cid}",
    ]
    if key:
        lines.append(f"UNIQUE_API_KEY={key}")
    if aid:
        lines.append(f"UNIQUE_APP_ID={aid}")
    if base:
        lines.append(f"UNIQUE_API_BASE={base}")

    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    env_file.chmod(0o600)
    typer.echo(f"Created {env_file}")

    if set_default:
        set_default_slot(slot)
        typer.echo(f"Default slot set to {slot!r}.")
    elif not non_interactive:
        if typer.confirm(f"Set {slot!r} as the default slot?", default=False):
            set_default_slot(slot)
            typer.echo(f"Default slot set to {slot!r}.")
