"""Config loader for the unique-websearch CLI.

Supports two configuration sources, checked in order:

1. **Full platform config** — written by the Claude Agent runner from the
   event payload.  The JSON is the complete ``WebSearchConfig`` serialised
   in camelCase (e.g. ``searchEngineConfig``, ``crawlerConfig``).  When
   detected the file is parsed with ``WebSearchConfig.model_validate()``
   so engine and crawler selection comes from the config, not from env
   vars.

2. **Env vars + optional simple overrides** — the legacy path.  Engine
   and crawler selection is determined by ``ACTIVE_SEARCH_ENGINES`` /
   ``ACTIVE_INHOUSE_CRAWLERS`` environment variables.  An optional JSON
   file provides non-secret overrides such as ``fetch_size``.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from unique_web_search.services.crawlers import (
    CRAWLER_NAME_TO_CONFIG,
    CrawlerConfigTypes,
)
from unique_web_search.services.search_engine import (
    ENGINE_NAME_TO_CONFIG,
    SearchEngineConfigTypes,
)
from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".unique-websearch.json"
ENV_CONFIG_PATH = "UNIQUE_WEBSEARCH_CONFIG"

DEFAULT_FETCH_SIZE = 50

_MODE_KEYS = frozenset({"webSearchActiveMode", "web_search_active_mode"})

_ENGINE_DISCRIMINATORS = frozenset({"search_engine_name", "searchEngineName"})
_CRAWLER_DISCRIMINATORS = frozenset({"crawler_type", "crawlerType"})


class CLIConfigError(Exception):
    pass


def _resolve_config_path(explicit_path: str | None = None) -> Path | None:
    """Return the config file path, or None if no file is found."""
    if explicit_path:
        p = Path(explicit_path)
        if not p.exists():
            raise CLIConfigError(f"Config file not found: {p}")
        return p
    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        p = Path(env_path)
        if not p.exists():
            raise CLIConfigError(
                f"Config file not found: {p} (set via {ENV_CONFIG_PATH})"
            )
        return p
    default = DEFAULT_CONFIG_PATH
    return default if default.exists() else None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CLIConfigError(f"Invalid JSON in {path}: {e}") from e


def _nested_has_discriminator(
    data: dict[str, Any],
    nested_keys: tuple[str, ...],
    discriminators: frozenset[str],
) -> bool:
    """Check whether any of *nested_keys* in *data* is a dict containing a discriminator."""
    for key in nested_keys:
        value = data.get(key)
        if isinstance(value, dict) and (set(value.keys()) & discriminators):
            return True
    return False


def _is_full_platform_config(data: dict[str, Any]) -> bool:
    """True when *data* looks like a full ``WebSearchConfig`` from the event.

    A full config is distinguished from a simple override file by the
    presence of the ``webSearchActiveMode`` top-level key **or**
    discriminator fields (``search_engine_name``, ``crawler_type``) inside
    the nested engine/crawler dicts — simple override files contain only
    flat scalar overrides like ``{"fetch_size": 50}``.
    """
    if set(data.keys()) & _MODE_KEYS:
        return True

    if _nested_has_discriminator(
        data,
        ("searchEngineConfig", "search_engine_config"),
        _ENGINE_DISCRIMINATORS,
    ):
        return True

    if _nested_has_discriminator(
        data,
        ("crawlerConfig", "crawler_config"),
        _CRAWLER_DISCRIMINATORS,
    ):
        return True

    return False


def _parse_full_config(
    data: dict[str, Any],
) -> tuple[SearchEngineConfigTypes, CrawlerConfigTypes]:
    """Parse a full ``WebSearchConfig`` dict (camelCase or snake_case).

    Uses the Pydantic model directly so that discriminated unions, aliases,
    validators, and defaults all work identically to the server.
    """
    from unique_web_search.config import WebSearchConfig

    try:
        parsed = WebSearchConfig.model_validate(data)
    except Exception as e:
        raise CLIConfigError(
            f"Failed to parse full WebSearchConfig from config file: {e}"
        ) from e

    _LOGGER.info(
        "Loaded full platform WebSearchConfig — engine: %s, crawler: %s, mode: %s",
        parsed.search_engine_config.search_engine_name,
        parsed.crawler_config.crawler_type,
        parsed.web_search_active_mode,
    )
    return parsed.search_engine_config, parsed.crawler_config


def _build_engine_config(
    overrides: dict[str, Any] | None = None,
) -> SearchEngineConfigTypes:
    """Build the search engine config from env_settings + optional JSON overrides."""
    engines = env_settings.active_search_engines
    if not engines:
        raise CLIConfigError(
            "No active search engine configured. "
            "Set the ACTIVE_SEARCH_ENGINES environment variable."
        )

    engine_key = engines[0].lower()
    config_cls = ENGINE_NAME_TO_CONFIG.get(engine_key)
    if config_cls is None:
        raise CLIConfigError(
            f"Unknown search engine: {engine_key!r}\n"
            f"Supported: {', '.join(sorted(ENGINE_NAME_TO_CONFIG.keys()))}"
        )

    kwargs: dict[str, Any] = {}
    if overrides:
        kwargs.update(overrides)

    if "fetch_size" not in kwargs:
        kwargs["fetch_size"] = DEFAULT_FETCH_SIZE

    try:
        return config_cls(**kwargs)
    except Exception as e:
        raise CLIConfigError(f"Invalid search engine config: {e}") from e


def _build_crawler_config(
    overrides: dict[str, Any] | None = None,
) -> CrawlerConfigTypes:
    """Build the crawler config from env_settings + optional JSON overrides."""
    crawlers = env_settings.active_crawlers
    if not crawlers:
        raise CLIConfigError(
            "No active crawler configured. "
            "Set the ACTIVE_INHOUSE_CRAWLERS environment variable."
        )

    crawler_key = crawlers[0].lower()
    config_cls = CRAWLER_NAME_TO_CONFIG.get(crawler_key)
    if config_cls is None:
        raise CLIConfigError(
            f"Unknown crawler: {crawler_key!r}\n"
            f"Supported: {', '.join(sorted(CRAWLER_NAME_TO_CONFIG.keys()))}"
        )

    kwargs: dict[str, Any] = {}
    if overrides:
        kwargs.update(overrides)

    try:
        return config_cls(**kwargs)
    except Exception as e:
        raise CLIConfigError(f"Invalid crawler config: {e}") from e


def load_search_engine_config(
    config_path: str | None = None,
) -> SearchEngineConfigTypes:
    """Load the search engine config for the ``search`` subcommand."""
    path = _resolve_config_path(config_path)

    if path is not None:
        data = _load_json(path)
        _LOGGER.info("Loaded CLI config from %s", path)

        if _is_full_platform_config(data):
            engine_cfg, _ = _parse_full_config(data)
            return engine_cfg

        engine_overrides = data.get("search_engine_config")
    else:
        engine_overrides = None

    engine_config = _build_engine_config(engine_overrides)
    _LOGGER.info("Using search engine: %s", engine_config.search_engine_name)
    return engine_config


def load_crawler_config(
    config_path: str | None = None,
) -> CrawlerConfigTypes:
    """Load the crawler config for the ``crawl`` subcommand."""
    path = _resolve_config_path(config_path)

    if path is not None:
        data = _load_json(path)
        _LOGGER.info("Loaded CLI config from %s", path)

        if _is_full_platform_config(data):
            _, crawler_cfg = _parse_full_config(data)
            return crawler_cfg

        crawler_overrides = data.get("crawler_config")
    else:
        crawler_overrides = None

    crawler_config = _build_crawler_config(crawler_overrides)
    _LOGGER.info("Using crawler: %s", crawler_config.crawler_type)
    return crawler_config
