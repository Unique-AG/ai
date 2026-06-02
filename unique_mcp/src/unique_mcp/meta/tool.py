from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, TypeVar

from dotenv import dotenv_values
from fastmcp.dependencies import CurrentFastMCP, Depends
from pydantic import BaseModel

from unique_mcp.meta.keys import CONFIG_META_KEY
from unique_mcp.util.find_env_file import find_env_file

_T = TypeVar("_T", bound=BaseModel)


def _config_env_key(server_name: str, config_model: type) -> str:
    """Derive env var key: UNIQUE_MCP_TOOL_{SERVER}_{CONFIG}_CONFIG.

    Example: ``mcp-search`` + ``SearchToolConfig``
    → ``UNIQUE_MCP_TOOL_MCP_SEARCH_SEARCH_TOOL_CONFIG``
    """
    server_part = re.sub(r"[^A-Za-z0-9]+", "_", server_name).strip("_").upper()
    config_name = re.sub(r"Config$", "", config_model.__name__)
    # NOTE: simple lookbehind regex — consecutive uppercase (e.g. "URL") becomes
    # "U_R_L". Acceptable for typical PascalCase config names; avoid acronym-only names.
    config_snake = re.sub(r"(?<!^)(?=[A-Z])", "_", config_name).upper()
    return f"UNIQUE_MCP_TOOL_{server_part}_{config_snake}_CONFIG"


@lru_cache(maxsize=32)
def _resolve_tool_env_file(
    environment_file_path: str | None,
    _cache_key_cwd: str,  # cache-busting key only; invalidates on dir change
) -> str | None:
    if environment_file_path and Path(environment_file_path).is_file():
        return environment_file_path
    env_file = find_env_file(filenames=["unique_mcp.env", ".env"], required=False)
    return str(env_file) if env_file else None


def _load_tool_config_override(env_key: str) -> str | None:
    """Load a tool config override from process env or env file."""
    if val := os.environ.get(env_key):
        return val
    env_file = _resolve_tool_env_file(
        os.environ.get("ENVIRONMENT_FILE_PATH"), _cache_key_cwd=os.getcwd()
    )
    if not env_file:
        return None
    return dotenv_values(env_file).get(env_key)


def get_tool_config(config_model: type[_T]) -> Callable[..., _T]:
    """Dependency factory — resolves and validates tool config.

    Lookup order:
      1. ``_meta[CONFIG_META_KEY]`` — injected by host at callTool time
      2. ``UNIQUE_MCP_TOOL_{SERVER}_{CONFIG}_CONFIG`` override from process env
         (and env files resolved by ``find_env_file(["unique_mcp.env", ".env"])``)
      3. ``config_model`` defaults

    Use as a default value in tool signatures::

        config: MyConfig = get_tool_config(MyConfig)
    """
    from unique_mcp.unique_injectors import get_request_meta  # avoid circular

    def _inner() -> _T:
        server = CurrentFastMCP()
        raw = (get_request_meta() or {}).get(CONFIG_META_KEY)
        if raw is not None:
            if isinstance(raw, str):
                return config_model.model_validate_json(raw)
            return config_model.model_validate(raw)

        env_key = _config_env_key(server.name, config_model)
        env_val = _load_tool_config_override(env_key)
        if env_val:
            return config_model.model_validate_json(env_val)

        return config_model()

    return _inner


__all__ = [
    "get_tool_config",
]
