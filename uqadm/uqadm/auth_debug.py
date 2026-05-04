"""Print resolved credential context when API calls fail with auth-like errors."""

from __future__ import annotations

import click
from unique_sdk import AuthenticationError
from unique_sdk.cli.config import Config


def is_likely_auth_failure(exc: BaseException) -> bool:
    """Heuristic: 401, AuthenticationError, or common unauthorized wording."""
    if isinstance(exc, AuthenticationError):
        return True
    status = getattr(exc, "http_status", None)
    if status == 401:
        return True
    lowered = str(exc).lower()
    if "unauthorized" in lowered or "401" in lowered:
        return True
    return False


def _describe_api_key(api_key: str) -> str:
    if not api_key:
        return (
            "(empty — often OK on localhost / secured cluster; otherwise set "
            "UNIQUE_API_KEY)"
        )
    n = len(api_key)
    if n <= 12:
        return f"set, length {n} (redacted)"
    return f"set, length {n}, prefix {api_key[:8]}…, suffix …{api_key[-4:]}"


def _describe_optional(value: str, *, empty_label: str) -> str:
    stripped = value.strip()
    if not stripped:
        return empty_label
    return repr(stripped)


def format_credential_debug_lines(
    cfg: Config,
    *,
    label: str | None = None,
    exc: BaseException | None = None,
) -> list[str]:
    """Human-readable lines (no full secrets); suitable for stderr."""
    title = "Credential snapshot (values after slot env load + SDK normalization)"
    lines: list[str] = [title + ":"]
    if label:
        lines.append(f"  Context: {label}")
    lines.extend(
        [
            f"  UNIQUE_USER_ID:     {cfg.user_id!r}",
            f"  UNIQUE_COMPANY_ID:  {cfg.company_id!r}",
            f"  UNIQUE_APP_ID:      {_describe_optional(cfg.app_id, empty_label='(empty)')}",
            f"  UNIQUE_API_BASE:    {cfg.api_base!r}",
            f"  UNIQUE_API_KEY:     {_describe_api_key(cfg.api_key)}",
        ]
    )
    if exc is not None:
        status = getattr(exc, "http_status", None)
        if status is not None:
            lines.append(f"  API HTTP status:     {status!r}")
        rid = getattr(exc, "request_id", None)
        if rid:
            lines.append(f"  API Request-Id:      {rid!r}")
    lines.append(
        "  (Toolkit-style unique_auth_*, unique_app_*, and unique_api_* names in "
        "the env file are copied into UNIQUE_* when the latter are unset; "
        "UNIQUE_* wins when both are set.)"
    )
    return lines


def echo_credential_debug_if_auth_failure(
    cfg: Config,
    exc: BaseException,
    *,
    label: str | None = None,
) -> None:
    """If ``exc`` looks like an auth problem, print ``cfg`` to stderr."""
    if not is_likely_auth_failure(exc):
        return
    click.echo("", err=True)
    for line in format_credential_debug_lines(cfg, label=label, exc=exc):
        click.echo(line, err=True)
