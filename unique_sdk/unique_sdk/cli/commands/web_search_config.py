"""Config-file loading for the unique-cli ``web-search`` subcommands.

Mirrors the discovery and shape rules of the reference ``unique-websearch``
CLI so the same config files work with both tools, but resolves the
config to plain dicts that are forwarded as ``searchEngineConfig`` /
``crawlerConfig`` payloads on the public API. Engine and crawler
selection is still performed server-side from the active env config; the
file just provides per-call overrides.

Two file shapes are recognised:

1. **Full platform config** — a complete ``WebSearchConfig`` payload as
   emitted by the platform (camelCase or snake_case). Detected by the
   presence of ``webSearchActiveMode`` / ``web_search_active_mode`` or a
   discriminator field (``search_engine_name`` / ``searchEngineName``,
   ``crawler`` / ``crawler_type`` / ``crawlerType``) inside the nested engine/crawler
   dicts. The nested ``searchEngineConfig`` and ``crawlerConfig`` blocks
   are forwarded verbatim to the API.

2. **Simple overrides** — a flat overrides file such as
   ``{"search_engine_config": {"fetch_size": 50}}`` (the legacy shape
   used by the reference CLI). Without a discriminator we cannot pin an
   engine server-side, so only well-known scalar overrides are
   extracted: today that means a default ``fetch_size`` /
   ``fetchSize`` for ``--fetch-size``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path.home() / ".unique-websearch.json"
ENV_CONFIG_PATH = "UNIQUE_WEBSEARCH_CONFIG"

_MODE_KEYS = frozenset({"webSearchActiveMode", "web_search_active_mode"})
_ENGINE_DISCRIMINATORS = frozenset({"search_engine_name", "searchEngineName"})
_CRAWLER_DISCRIMINATORS = frozenset({"crawler", "crawler_type", "crawlerType"})

_ENGINE_KEYS = ("searchEngineConfig", "search_engine_config")
_CRAWLER_KEYS = ("crawlerConfig", "crawler_config")


class WebSearchCLIConfigError(Exception):
    """Raised when the CLI cannot load or interpret the config file."""


@dataclass(frozen=True)
class ConfigOverrides:
    """Resolved overrides from a CLI config file.

    Attributes:
        engine_config: Full ``searchEngineConfig`` dict to forward to the
            API, or ``None`` when no override applies.
        crawler_config: Full ``crawlerConfig`` dict to forward to the
            API, or ``None`` when no override applies.
        fetch_size: Default ``fetchSize`` extracted from a simple-override
            file; only meaningful when ``engine_config`` is ``None``.
    """

    engine_config: dict[str, Any] | None = None
    crawler_config: dict[str, Any] | None = None
    fetch_size: int | None = None

    @property
    def is_empty(self) -> bool:
        return (
            self.engine_config is None
            and self.crawler_config is None
            and self.fetch_size is None
        )


def resolve_config_path(explicit_path: str | None = None) -> Path | None:
    """Locate a config file, mirroring ``unique-websearch`` discovery.

    Order of resolution:

    1. ``explicit_path`` (from ``--config``) — must exist if set.
    2. ``$UNIQUE_WEBSEARCH_CONFIG`` — must exist if set.
    3. ``~/.unique-websearch.json`` — used only if it exists.

    Returns ``None`` when no file is configured or the default is absent.
    """
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if not path.exists():
            raise WebSearchCLIConfigError(f"Config file not found: {path}")
        return path

    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        path = Path(env_path).expanduser()
        if not path.exists():
            raise WebSearchCLIConfigError(
                f"Config file not found: {path} (set via {ENV_CONFIG_PATH})"
            )
        return path

    default = DEFAULT_CONFIG_PATH
    return default if default.exists() else None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WebSearchCLIConfigError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WebSearchCLIConfigError(
            f"Config file {path} must contain a JSON object at the top level."
        )
    return data


def _nested_has_discriminator(
    data: dict[str, Any],
    nested_keys: tuple[str, ...],
    discriminators: frozenset[str],
) -> bool:
    """Return ``True`` if any nested dict carries a discriminator key."""
    for key in nested_keys:
        value = data.get(key)
        if isinstance(value, dict) and (set(value.keys()) & discriminators):
            return True
    return False


def is_full_platform_config(data: dict[str, Any]) -> bool:
    """Detect the "full ``WebSearchConfig``" shape vs. a simple-override file.

    A full config is identified by the ``webSearchActiveMode`` /
    ``web_search_active_mode`` top-level key, or by a discriminator
    (``searchEngineName`` / ``crawlerType``) inside the nested
    engine/crawler config dicts.
    """
    if set(data.keys()) & _MODE_KEYS:
        return True
    if _nested_has_discriminator(data, _ENGINE_KEYS, _ENGINE_DISCRIMINATORS):
        return True
    if _nested_has_discriminator(data, _CRAWLER_KEYS, _CRAWLER_DISCRIMINATORS):
        return True
    return False


def _first_present(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first value among ``keys`` present in ``data``, else ``None``."""
    for key in keys:
        if key in data:
            return data[key]
    return None


def _extract_simple_fetch_size(data: dict[str, Any]) -> int | None:
    """Pull ``fetch_size`` / ``fetchSize`` out of a simple-overrides file."""
    block = _first_present(data, _ENGINE_KEYS)
    if not isinstance(block, dict):
        return None
    raw = _first_present(block, ("fetchSize", "fetch_size"))
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise WebSearchCLIConfigError(
            f"Config field fetch_size must be an integer (got {raw!r})."
        )
    if raw < 1:
        raise WebSearchCLIConfigError(
            f"Config field fetch_size must be >= 1 (got {raw})."
        )
    return raw


def parse_config_data(data: dict[str, Any]) -> ConfigOverrides:
    """Project a parsed config-file dict into ``ConfigOverrides``.

    Full-platform configs forward the nested engine/crawler dicts
    verbatim. Simple-override configs only contribute a ``fetch_size``
    default today; other scalar overrides are intentionally ignored
    because the server cannot apply them without a discriminator.
    """
    if is_full_platform_config(data):
        engine_block = _first_present(data, _ENGINE_KEYS)
        crawler_block = _first_present(data, _CRAWLER_KEYS)
        return ConfigOverrides(
            engine_config=engine_block if isinstance(engine_block, dict) else None,
            crawler_config=crawler_block if isinstance(crawler_block, dict) else None,
        )
    return ConfigOverrides(fetch_size=_extract_simple_fetch_size(data))


def load_overrides(config_path: str | None = None) -> ConfigOverrides:
    """Resolve a config file (if any) and return the projected overrides.

    Returns an empty :class:`ConfigOverrides` when no config file is
    discovered, so callers can unconditionally apply the result.
    """
    path = resolve_config_path(config_path)
    if path is None:
        return ConfigOverrides()
    return parse_config_data(_load_json(path))
