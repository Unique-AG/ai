"""Load per-slot env files and apply SDK CLI config."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from unique_sdk.cli.config import Config, load_config

from uqadm.core.paths import envs_dir

UNIQUE_ENV_KEYS = (
    "UNIQUE_USER_ID",
    "UNIQUE_COMPANY_ID",
    "UNIQUE_API_KEY",
    "UNIQUE_APP_ID",
    "UNIQUE_API_BASE",
)

# Toolkit UniqueAuth-style keys (unique_toolkit UniqueAuth); cleared with UNIQUE_* on slot switch.
TOOLKIT_AUTH_ENV_KEYS = (
    "unique_auth_user_id",
    "unique_auth_company_id",
    "UNIQUE_AUTH_USER_ID",
    "UNIQUE_AUTH_COMPANY_ID",
)

# Toolkit UniqueApp / UniqueApi (unique_toolkit); cleared on slot switch.
TOOLKIT_APP_ENV_KEYS = (
    "unique_app_id",
    "unique_app_key",
    "UNIQUE_APP_KEY",
    "unique_app_endpoint_secret",
    "UNIQUE_APP_ENDPOINT_SECRET",
)
TOOLKIT_API_ENV_KEYS = (
    "unique_api_base_url",
    "UNIQUE_API_BASE_URL",
    "unique_api_version",
    "UNIQUE_API_VERSION",
)


class MissingSlotEnvFileError(FileNotFoundError):
    """Raised when neither ``.{slot}.env`` nor ``{slot}.env`` exists for a slot."""


class MissingEnvCredentialsError(RuntimeError):
    """Raised when ``UQADM_AUTH_FROM_ENV`` is set but required vars are absent."""


_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def auth_from_env_enabled() -> bool:
    """Whether to authenticate straight from the process environment.

    When ``UQADM_AUTH_FROM_ENV`` is set to a truthy value (``1``, ``true``,
    ``yes``, ``on`` — case-insensitive), uqadm reads credentials from the
    already-exported ``UNIQUE_*``/toolkit variables and skips per-slot ``.env``
    files entirely. Any other value (including ``0``/``false``) or an unset
    variable leaves the file-based path in effect.
    """
    raw = os.environ.get("UQADM_AUTH_FROM_ENV")
    return raw is not None and raw.strip().lower() in _TRUTHY_ENV_VALUES


def _format_missing_slot_env_help(
    slot: str, searched_dirs: list[Path], hidden_name: str, visible_name: str
) -> str:
    """Human-oriented explanation of what was searched and what to do next."""
    dir_lines = "\n".join(f"  {d.resolve()}" for d in searched_dirs)
    return (
        f"uqadm: no credentials file found for slot {slot!r}.\n\n"
        "Searched in these directories (in order):\n"
        f"{dir_lines}\n\n"
        "Looked for exactly these filenames (must be regular files, not directories):\n"
        f"  1. {hidden_name}\n"
        "       — tried first; if this file exists it is always used\n"
        f"  2. {visible_name}\n"
        f"       — used only when {hidden_name} does not exist\n\n"
        "Neither file was found. Create one of them. Minimum contents (either naming style):\n"
        "  UNIQUE_USER_ID=<your user id>   OR   unique_auth_user_id=<your user id>\n"
        "     (also accepted: UNIQUE_AUTH_USER_ID)\n"
        "  UNIQUE_COMPANY_ID=<your company id>   OR   unique_auth_company_id=<your company id>\n"
        "     (also accepted: UNIQUE_AUTH_COMPANY_ID)\n"
        "If both UNIQUE_* and toolkit-style names are set, UNIQUE_* wins.\n"
        "Optional API lines (SDK or toolkit naming):\n"
        "  UNIQUE_API_KEY / UNIQUE_APP_ID / UNIQUE_API_BASE\n"
        "  OR unique_app_key / unique_app_id / unique_api_base_url\n"
        "     (also: UNIQUE_APP_KEY, UNIQUE_API_BASE_URL)\n\n"
        "Run `uqadm env create <slot>` to create a slot interactively,\n"
        "or `uqadm install` to set up uqadm from scratch.\n\n"
        'For a full example, see the README section "Credential slots and env files".'
    )


def _sdk_api_base_from_toolkit_api_base_url(raw: str) -> str:
    """Derive ``UNIQUE_API_BASE`` from toolkit ``UniqueApi.base_url``.

    **Host-only** (no path, or path ``/`` only): append ``/public/chat``.
    **Any non-root path**: return the value unchanged.
    """
    cleaned = raw.strip().strip("'\"")
    parsed = urlparse(cleaned)
    path = parsed.path or ""
    if path in ("", "/"):
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc
        return urlunparse((scheme, netloc, "/public/chat", "", "", ""))
    return cleaned


def _first_nonempty_env(*keys: str) -> str | None:
    for key in keys:
        raw = os.environ.get(key)
        if raw is not None and raw.strip():
            return raw.strip()
    return None


def _sync_sdk_env_from_toolkit_aliases() -> None:
    """Copy toolkit-style env names into ``UNIQUE_*`` when those SDK vars are unset."""
    if not _first_nonempty_env("UNIQUE_USER_ID"):
        alt = _first_nonempty_env("unique_auth_user_id", "UNIQUE_AUTH_USER_ID")
        if alt is not None:
            os.environ["UNIQUE_USER_ID"] = alt
    if not _first_nonempty_env("UNIQUE_COMPANY_ID"):
        alt = _first_nonempty_env(
            "unique_auth_company_id",
            "UNIQUE_AUTH_COMPANY_ID",
        )
        if alt is not None:
            os.environ["UNIQUE_COMPANY_ID"] = alt

    if not _first_nonempty_env("UNIQUE_API_KEY"):
        alt = _first_nonempty_env("unique_app_key", "UNIQUE_APP_KEY")
        if alt is not None:
            os.environ["UNIQUE_API_KEY"] = alt

    if not _first_nonempty_env("UNIQUE_APP_ID"):
        alt = _first_nonempty_env("unique_app_id")
        if alt is not None:
            os.environ["UNIQUE_APP_ID"] = alt

    if not _first_nonempty_env("UNIQUE_API_BASE"):
        alt = _first_nonempty_env("unique_api_base_url", "UNIQUE_API_BASE_URL")
        if alt is not None:
            os.environ["UNIQUE_API_BASE"] = _sdk_api_base_from_toolkit_api_base_url(alt)


def env_file_for_slot(slot: str, cwd: Path | None = None) -> Path:
    """Resolve the env file path for ``slot``.

    Resolution order:
    1. ``cwd`` if explicitly passed (back-compat / ``--cwd`` override).
    2. ``envs_dir()`` — the standard ``~/.uqadm/envs/`` location.
    3. Process cwd — legacy fallback so existing ad-hoc layouts still work.

    Raises:
        MissingSlotEnvFileError: If no matching env file is found in any location.
    """
    hidden_name = f".{slot}.env"
    visible_name = f"{slot}.env"

    search_dirs: list[Path] = []
    if cwd is not None:
        search_dirs.append(cwd)
    search_dirs.append(envs_dir())
    search_dirs.append(Path.cwd())

    # Deduplicate while preserving order (cwd might equal envs_dir or process cwd).
    seen: set[Path] = set()
    unique_dirs: list[Path] = []
    for d in search_dirs:
        resolved = d.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_dirs.append(d)

    for base in unique_dirs:
        hidden = base / hidden_name
        visible = base / visible_name
        if hidden.is_file():
            return hidden
        if visible.is_file():
            return visible

    raise MissingSlotEnvFileError(
        _format_missing_slot_env_help(slot, unique_dirs, hidden_name, visible_name)
    )


def clear_unique_env_vars() -> None:
    """Remove UNIQUE_* and toolkit env keys so switching slots does not leak."""
    for key in UNIQUE_ENV_KEYS:
        os.environ.pop(key, None)
    for key in TOOLKIT_AUTH_ENV_KEYS:
        os.environ.pop(key, None)
    for key in TOOLKIT_APP_ENV_KEYS:
        os.environ.pop(key, None)
    for key in TOOLKIT_API_ENV_KEYS:
        os.environ.pop(key, None)


def _require_min_credentials() -> None:
    """Ensure the mandatory SDK vars are present when authing from the env."""
    missing = [
        key
        for key in ("UNIQUE_USER_ID", "UNIQUE_COMPANY_ID")
        if not _first_nonempty_env(key)
    ]
    if missing:
        raise MissingEnvCredentialsError(
            "uqadm: UQADM_AUTH_FROM_ENV is set but these required variables are "
            f"missing from the environment: {', '.join(missing)}.\n\n"
            "Set them directly (UNIQUE_USER_ID, UNIQUE_COMPANY_ID) or via toolkit "
            "aliases (unique_auth_user_id, unique_auth_company_id), or unset "
            "UQADM_AUTH_FROM_ENV to use a per-slot .env file instead."
        )


def load_slot(slot: str, cwd: Path | None = None) -> Path | None:
    """Load slot credentials into ``os.environ``.

    When ``UQADM_AUTH_FROM_ENV`` is set, credentials are taken from the current
    environment (no file, no clearing) and ``None`` is returned. Otherwise the
    resolved slot env file is loaded with ``override=True``.
    """
    if auth_from_env_enabled():
        # The shell environment is the source of truth; do not clear it.
        _sync_sdk_env_from_toolkit_aliases()
        _require_min_credentials()
        return None
    path = env_file_for_slot(slot, cwd)
    clear_unique_env_vars()
    _: bool = load_dotenv(path, override=True)
    _sync_sdk_env_from_toolkit_aliases()
    return path


def config_for_slot(slot: str, cwd: Path | None = None) -> Config:
    """Load slot env file and run the same wiring as ``unique-cli``."""
    load_slot(slot, cwd)
    return load_config()


def normalize_api_base(url: str) -> str:
    """Normalize API base URL for same-environment comparison."""
    return url.rstrip("/")
