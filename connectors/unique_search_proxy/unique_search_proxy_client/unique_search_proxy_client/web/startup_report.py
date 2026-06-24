from __future__ import annotations

import logging
import os
from collections import defaultdict

from pydantic import BaseModel

from unique_search_proxy_client.web.helm.registry import startup_report_groups
from unique_search_proxy_client.web.settings.secret_str import (
    field_has_not_provided_default,
    is_secret_configured,
)

_LOGGER = logging.getLogger(__name__)


def _env_var_name(field_name: str, env_prefix: str) -> str:
    return f"{env_prefix}{field_name.upper()}"


def _field_status(
    model: BaseModel,
    field_name: str,
    env_prefix: str,
) -> str:
    value = getattr(model, field_name)
    field_info = model.model_fields[field_name]
    env_var = _env_var_name(field_name, env_prefix)

    if field_has_not_provided_default(field_info):
        return "configured" if is_secret_configured(value) else "missing"

    if value is None:
        return "unset"

    if env_var in os.environ:
        return "set"

    return "default"


def _group_fields_by_status(
    model: BaseModel,
    env_prefix: str,
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for field_name in model.model_fields:
        env_var = _env_var_name(field_name, env_prefix)
        status = _field_status(model, field_name, env_prefix)
        grouped[status].append(env_var)
    return grouped


def _group_summary(grouped: dict[str, list[str]]) -> str:
    missing = grouped.get("missing", [])
    if missing:
        return f"incomplete ({len(missing)} missing)"
    return "ready"


def _format_settings_value(value: object) -> str:
    if isinstance(value, dict):
        if not value:
            return "{}"
        pairs = ", ".join(f"{key!r}: {secret}" for key, secret in value.items())
        return "{" + pairs + "}"
    return str(value)


def _format_group(title: str, model: BaseModel, env_prefix: str) -> list[str]:
    grouped = _group_fields_by_status(model, env_prefix)
    lines = [f"  [{title}] {_group_summary(grouped)}"]
    for field_name in model.model_fields:
        env_var = _env_var_name(field_name, env_prefix)
        value = getattr(model, field_name)
        lines.append(f"    {env_var}={_format_settings_value(value)}")
    return lines


def build_startup_settings_report() -> str:
    """Build a multi-line startup settings summary for logging."""
    lines = ["Search Proxy settings at startup:"]
    for title, model, env_prefix in startup_report_groups():
        lines.extend(_format_group(title, model, env_prefix))
    lines.append(f"  [Runtime] LOG_LEVEL={os.getenv('LOG_LEVEL', 'INFO')}")
    return "\n".join(lines)


def log_startup_settings_report(logger: logging.Logger | None = None) -> None:
    """Log configured vs missing/default env-backed settings at pod startup."""
    log = logger or _LOGGER
    log.info("%s", build_startup_settings_report())
