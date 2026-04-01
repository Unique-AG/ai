"""JSON config loader for the unique-websearch CLI."""

from __future__ import annotations

import json
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

DEFAULT_CONFIG_PATH = Path.home() / ".unique-websearch.json"
ENV_CONFIG_PATH = "UNIQUE_WEBSEARCH_CONFIG"

SUPPORTED_ENGINES = sorted(ENGINE_NAME_TO_CONFIG.keys())
SUPPORTED_CRAWLERS = sorted(CRAWLER_NAME_TO_CONFIG.keys())


class CLIConfigError(Exception):
    pass


def _resolve_config_path(explicit_path: str | None = None) -> Path:
    if explicit_path:
        return Path(explicit_path)
    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_PATH


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise CLIConfigError(
            f"Config file not found: {path}\n"
            f"Create it or set {ENV_CONFIG_PATH} to point to your config.\n\n"
            f"Minimal example:\n"
            f"{{\n"
            f'  "search_engine_config": {{\n'
            f'    "search_engine_name": "Google",\n'
            f'    "fetch_size": 5\n'
            f"  }},\n"
            f'  "crawler_config": {{\n'
            f'    "crawler_type": "BasicCrawler",\n'
            f'    "timeout": 10\n'
            f"  }}\n"
            f"}}"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CLIConfigError(f"Invalid JSON in {path}: {e}") from e


def _build_engine_config(
    raw: dict[str, Any],
    engine_override: str | None = None,
) -> SearchEngineConfigTypes:
    engine_data = dict(raw)

    if engine_override:
        engine_data["search_engine_name"] = _engine_display_name(engine_override)

    name_raw = engine_data.get("search_engine_name")
    if not name_raw:
        raise CLIConfigError(
            "search_engine_config.search_engine_name is required.\n"
            f"Supported engines: {', '.join(SUPPORTED_ENGINES)}"
        )

    lookup_key = _normalise_engine_key(name_raw)
    config_cls = ENGINE_NAME_TO_CONFIG.get(lookup_key)
    if config_cls is None:
        raise CLIConfigError(
            f"Unknown search engine: {name_raw!r}\n"
            f"Supported engines: {', '.join(SUPPORTED_ENGINES)}"
        )

    try:
        return config_cls(**engine_data)
    except Exception as e:
        raise CLIConfigError(f"Invalid search engine config: {e}") from e


def _build_crawler_config(raw: dict[str, Any]) -> CrawlerConfigTypes:
    crawler_data = dict(raw)
    name_raw = crawler_data.get("crawler_type")
    if not name_raw:
        raise CLIConfigError(
            "crawler_config.crawler_type is required.\n"
            f"Supported crawlers: {', '.join(SUPPORTED_CRAWLERS)}"
        )

    lookup_key = _normalise_crawler_key(name_raw)
    config_cls = CRAWLER_NAME_TO_CONFIG.get(lookup_key)
    if config_cls is None:
        raise CLIConfigError(
            f"Unknown crawler: {name_raw!r}\n"
            f"Supported crawlers: {', '.join(SUPPORTED_CRAWLERS)}"
        )

    try:
        return config_cls(**crawler_data)
    except Exception as e:
        raise CLIConfigError(f"Invalid crawler config: {e}") from e


def _normalise_engine_key(name: str) -> str:
    """Map display names like 'Google' or CLI args like 'google' to registry keys."""
    return name.lower().replace(" ", "_")


def _engine_display_name(cli_arg: str) -> str:
    """Map a CLI arg like 'google' to the SearchEngineType display name like 'Google'."""
    from unique_web_search.services.search_engine.base import SearchEngineType

    mapping = {t.value.lower().replace(" ", "_"): t.value for t in SearchEngineType}
    key = cli_arg.lower().replace(" ", "_")
    return mapping.get(key, cli_arg)


def _normalise_crawler_key(name: str) -> str:
    """Map display names like 'BasicCrawler' to registry keys like 'basic'."""
    from unique_web_search.services.crawlers.base import CrawlerType

    for ct in CrawlerType:
        if name == ct.value or name.lower() == ct.value.lower():
            return ct.name.lower()

    return name.lower().replace("crawler", "").strip("_").strip()


def load_websearch_config(
    config_path: str | None = None,
    engine_override: str | None = None,
) -> tuple[SearchEngineConfigTypes, CrawlerConfigTypes]:
    """Load and validate the CLI config, returning engine + crawler configs.

    Args:
        config_path: Explicit path to JSON config file.
        engine_override: Override search engine name from CLI flag.

    Returns:
        Tuple of (search_engine_config, crawler_config).
    """
    path = _resolve_config_path(config_path)
    data = _load_json(path)

    engine_raw = data.get("search_engine_config")
    if not isinstance(engine_raw, dict):
        raise CLIConfigError("Config must contain a 'search_engine_config' object.")

    crawler_raw = data.get("crawler_config")
    if not isinstance(crawler_raw, dict):
        raise CLIConfigError("Config must contain a 'crawler_config' object.")

    engine_config = _build_engine_config(engine_raw, engine_override)
    crawler_config = _build_crawler_config(crawler_raw)

    return engine_config, crawler_config
