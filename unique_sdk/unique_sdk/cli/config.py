"""Configuration from environment variables, wired into unique_sdk globals."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import unique_sdk

CONFIG_PATH_ENV = "UNIQUE_CONFIG_PATH"

# Keys a UNIQUE_CONFIG_PATH file may provide. Anything else in the file is
# ignored so a config file can never inject arbitrary environment variables.
CONFIG_FILE_KEYS = (
    "UNIQUE_API_KEY",
    "UNIQUE_APP_ID",
    "UNIQUE_USER_ID",
    "UNIQUE_COMPANY_ID",
    "UNIQUE_API_BASE",
    "UNIQUE_SKILL_FOLDER",
    "INGESTION_UPLOAD_API_URL_INTERNAL",
)


class Config:
    """Holds resolved configuration values for the CLI session."""

    user_id: str
    company_id: str
    api_key: str
    app_id: str
    api_base: str
    ingestion_upload_api_url_internal: str | None

    def __init__(
        self,
        *,
        user_id: str | None,
        company_id: str | None,
        api_key: str,
        app_id: str,
        api_base: str,
        ingestion_upload_api_url_internal: str | None = None,
    ) -> None:
        self.user_id = cast(str, user_id)
        self.company_id = cast(str, company_id)
        self.api_key = api_key
        self.app_id = app_id
        self.api_base = api_base
        self.ingestion_upload_api_url_internal = ingestion_upload_api_url_internal


def apply_config_file_defaults() -> None:
    """Merge values from the ``UNIQUE_CONFIG_PATH`` JSON file into the env.

    The file is written by the Claude Code plugin's SessionStart hook
    (``unique-cli write-config``) so that plugin userConfig values reach
    CLI invocations from the Bash tool, where ``CLAUDE_PLUGIN_OPTION_*``
    variables are not available. Real environment variables always win;
    file values only fill gaps. Missing or malformed files are ignored —
    the normal "missing environment variables" error then explains what
    is required.
    """
    path = os.environ.get(CONFIG_PATH_ENV)
    if not path:
        return
    try:
        raw = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(raw, dict):
        return
    for key in CONFIG_FILE_KEYS:
        value = raw.get(key)
        if isinstance(value, str) and value and not os.environ.get(key):
            os.environ[key] = value


def load_config() -> Config:
    """Load configuration from environment variables and wire into unique_sdk.

    Sources (highest precedence first):
        1. Environment variables.
        2. A JSON config file pointed to by ``UNIQUE_CONFIG_PATH`` whose
           keys are the same environment variable names (written by the
           Claude Code plugin SessionStart hook via
           ``unique-cli write-config``).

    Required:
        * ``UNIQUE_USER_ID`` / ``UNIQUE_COMPANY_ID``.
        * ``UNIQUE_API_KEY`` / ``UNIQUE_APP_ID`` when connecting to a
          public Unique gateway.
    Optional:
        * ``UNIQUE_API_KEY`` / ``UNIQUE_APP_ID`` on localhost or in a
          secured cluster.
        * ``UNIQUE_API_BASE`` (defaults to the SDK default).
        * ``INGESTION_UPLOAD_API_URL_INTERNAL`` — when set, content
          uploads via ``unique_sdk.utils.file_io.upload_file`` rewrite
          the public ``writeUrl`` / ``pdfPreviewWriteUrl`` to this base
          before the PUT, so blob uploads can travel over a private
          cluster network. Empty / whitespace-only disables the rewrite
          (treated identically to unset).
    """
    apply_config_file_defaults()

    api_key = os.environ.get("UNIQUE_API_KEY", "")
    app_id = os.environ.get("UNIQUE_APP_ID", "")
    api_base = os.environ.get("UNIQUE_API_BASE", unique_sdk.api_base)
    api_base = api_base.strip().strip("'\"")

    missing: list[str] = []
    if _requires_api_credentials(api_base):
        for var in ("UNIQUE_API_KEY", "UNIQUE_APP_ID"):
            if not os.environ.get(var):
                missing.append(var)
    for var in ("UNIQUE_USER_ID", "UNIQUE_COMPANY_ID"):
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        print(
            f"Error: missing required environment variables for {api_base}: "
            f"{', '.join(missing)}",
            file=sys.stderr,
        )
        if "UNIQUE_API_KEY" in missing or "UNIQUE_APP_ID" in missing:
            print(
                "Set UNIQUE_API_KEY and UNIQUE_APP_ID when connecting to a "
                "public Unique gateway. They are only optional for localhost "
                "or secured cluster API bases.",
                file=sys.stderr,
            )
        sys.exit(1)

    user_id = os.environ["UNIQUE_USER_ID"]
    company_id = os.environ["UNIQUE_COMPANY_ID"]
    raw_ingestion_url = os.environ.get("INGESTION_UPLOAD_API_URL_INTERNAL")
    ingestion_upload_api_url_internal = (
        raw_ingestion_url.strip() or None
        if isinstance(raw_ingestion_url, str)
        else None
    )

    unique_sdk.api_key = api_key
    unique_sdk.app_id = app_id
    unique_sdk.api_base = api_base
    unique_sdk.ingestion_upload_api_url_internal = ingestion_upload_api_url_internal

    return Config(
        user_id=user_id,
        company_id=company_id,
        api_key=api_key,
        app_id=app_id,
        api_base=api_base,
        ingestion_upload_api_url_internal=ingestion_upload_api_url_internal,
    )


def write_config_file(out_path: Path) -> int:
    """Write present ``CONFIG_FILE_KEYS`` env values to a 0600 JSON file.

    Used by the Claude Code plugin's SessionStart hook, where the wrapper
    script has already bridged ``CLAUDE_PLUGIN_OPTION_*`` values into the
    ``UNIQUE_*`` variables. Values already stored in the file are preserved
    when the corresponding environment variable is unset, so a run with
    partial options never erases previously written credentials.
    Returns the number of values written.
    """
    existing: dict[str, object] = {}
    try:
        raw = json.loads(out_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            existing = raw
    except (OSError, json.JSONDecodeError):
        pass
    values = {
        key: value
        for key in CONFIG_FILE_KEYS
        if (value := os.environ.get(key) or existing.get(key))
        and isinstance(value, str)
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(values, handle, indent=2)
        handle.write("\n")
    # O_CREAT mode only applies to new files; enforce 0600 on rewrites too.
    os.chmod(out_path, 0o600)
    return len(values)


def _requires_api_credentials(api_base: str) -> bool:
    """Return whether API key and app ID are required for the API base."""
    parsed = urlparse(api_base)
    hostname = parsed.hostname or ""
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return False
    if hostname.endswith((".local", ".svc", ".cluster.local")):
        return False
    return True
