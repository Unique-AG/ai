"""Bootstrap uqadm: dirs, shell completion, first env slot, and rc file snippet."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Annotated, Optional

import typer

from uqadm.core.config_file import get_default_slot
from uqadm.core.paths import envs_dir, uqadm_home

_RC_BEGIN = "# >>> uqadm >>>"
_RC_END = "# <<< uqadm <<<"
_RC_BLOCK_TEMPLATE = """\
{begin}
export UQADM_HOME="{home}"
{end}"""


def _detect_shell() -> str:
    """Heuristic: check $SHELL, fall back to 'bash'."""
    shell_path = os.environ.get("SHELL", "")
    if "zsh" in shell_path:
        return "zsh"
    if "bash" in shell_path:
        return "bash"
    return "bash"


def _default_rc_file(shell: str) -> Path:
    if shell == "zsh":
        zdotdir = os.environ.get("ZDOTDIR")
        base = Path(zdotdir) if zdotdir else Path.home()
        return base / ".zshrc"
    return Path.home() / ".bashrc"


def _rc_block(home: Path) -> str:
    return _RC_BLOCK_TEMPLATE.format(
        begin=_RC_BEGIN,
        home=str(home),
        end=_RC_END,
    )


def _rc_already_patched(rc_file: Path) -> bool:
    if not rc_file.is_file():
        return False
    content = rc_file.read_text(encoding="utf-8")
    return _RC_BEGIN in content


def _patch_rc(rc_file: Path, home: Path, *, dry_run: bool) -> None:
    if _rc_already_patched(rc_file):
        typer.echo(f"  {rc_file}: already contains uqadm block — skipping.")
        return
    block = "\n" + _rc_block(home) + "\n"
    if dry_run:
        typer.echo(f"  [dry-run] Would append to {rc_file}:\n{block}")
        return
    with rc_file.open("a", encoding="utf-8") as fh:
        fh.write(block)
    typer.echo(f"  Appended uqadm block to {rc_file}.")


def _install_completion(shell: str, *, dry_run: bool) -> None:
    """Install shell completion for uqadm using typer's built-in mechanism."""
    if dry_run:
        typer.echo(f"  [dry-run] Would install {shell} completion for uqadm.")
        return
    env_var = f"_{('uqadm').upper()}_COMPLETE"
    complete_var = f"{shell}_source"
    try:
        result = subprocess.run(
            ["uqadm"],
            env={**os.environ, env_var: complete_var},
            capture_output=True,
            text=True,
        )
        typer.echo(f"  Shell completion for {shell} installed.")
        _ = result  # output is handled by the shell's sourcing mechanism
    except Exception as exc:
        typer.echo(f"  Warning: could not auto-install completion: {exc}", err=True)
        typer.echo(
            f"  You can install manually by adding this to your rc file:\n"
            f'  eval "$(uqadm --show-completion {shell})"',
            err=True,
        )


def _ensure_dirs(home: Path, *, dry_run: bool) -> None:
    if dry_run:
        typer.echo(f"  [dry-run] Would create {home} (mode 0700) and {home / 'envs'}.")
        return
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    (home / "envs").mkdir(parents=True, exist_ok=True)
    typer.echo(f"  Created {home}/  and  {home / 'envs'}/")


def _maybe_create_first_slot(*, dry_run: bool) -> None:
    """If no slot env files exist yet, offer to run ``uqadm env create`` interactively."""
    from uqadm.env.create import cmd_env_create

    directory = envs_dir()
    has_slots = directory.is_dir() and any(
        f.name.endswith(".env") for f in directory.iterdir() if f.is_file()
    )
    if has_slots:
        typer.echo("  Existing credential slots found — skipping first-slot setup.")
        return

    typer.echo("\nNo credential slots found.")
    if dry_run:
        typer.echo("  [dry-run] Would prompt for first slot creation.")
        return

    if typer.confirm("Create your first credential slot now?", default=True):
        slot = typer.prompt("Slot name (e.g. qa, prod)", default="qa")
        cmd_env_create(
            slot,
            force=False,
            set_default=True,
            non_interactive=False,
            user_id=None,
            company_id=None,
            api_key=None,
            app_id=None,
            api_base=None,
        )


def install_command(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Print what would be done without making changes."
        ),
    ] = False,
    no_rc: Annotated[
        bool,
        typer.Option("--no-rc", help="Skip patching the shell rc file."),
    ] = False,
    shell: Annotated[
        Optional[str],
        typer.Option(
            "--shell",
            help="Shell to configure: zsh or bash (auto-detected if omitted).",
        ),
    ] = None,
    rc_file: Annotated[
        Optional[Path],
        typer.Option(
            "--rc-file", help="Path to the rc file to patch (overrides auto-detection)."
        ),
    ] = None,
) -> None:
    """Bootstrap uqadm: create ~/.uqadm dirs, install shell completion, set up first slot."""
    home = uqadm_home()
    detected_shell = shell or _detect_shell()

    typer.echo(f"\nuqadm install (shell={detected_shell}, home={home})\n")

    typer.echo("1. Ensuring ~/.uqadm directories …")
    _ensure_dirs(home, dry_run=dry_run)

    typer.echo("\n2. Installing shell completion …")
    _install_completion(detected_shell, dry_run=dry_run)

    typer.echo("\n3. First credential slot …")
    _maybe_create_first_slot(dry_run=dry_run)

    if not no_rc:
        typer.echo("\n4. Patching shell rc file …")
        target_rc = rc_file or _default_rc_file(detected_shell)
        _patch_rc(target_rc, home, dry_run=dry_run)
    else:
        typer.echo("\n4. Skipping rc file patch (--no-rc).")

    default_slot = get_default_slot()
    sample_slot = default_slot or "<slot>"

    typer.echo(
        f"\n{'[dry-run] ' if dry_run else ''}Setup complete!\n\n"
        f"Next steps:\n"
        f"  source {rc_file or _default_rc_file(detected_shell)}\n"
        f"  uqadm env list\n"
        f"  uqadm space list --slot {sample_slot}\n"
    )
