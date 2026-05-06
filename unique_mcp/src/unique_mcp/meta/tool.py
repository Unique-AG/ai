from __future__ import annotations

import os
import re
from typing import Any, ClassVar, TypeVar

from fastmcp.dependencies import CurrentFastMCP, Depends
from pydantic import BaseModel
from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model

from unique_mcp.meta.keys import CONFIG_META_KEY, CONFIG_SCHEMA_META_KEY

_T = TypeVar("_T", bound=BaseModel)


class ConfigSchemaMeta:
    """MetaPart that publishes RJSF schema at listTools time."""

    _META_KEY: ClassVar[str] = CONFIG_SCHEMA_META_KEY

    def __init__(self, config_model: type[BaseModel]) -> None:
        self.config_model = config_model

    def merge_into_meta(self, meta: dict[str, Any]) -> None:
        meta[self._META_KEY] = {
            "json_schema": self.config_model.model_json_schema(),
            "ui_schema": ui_schema_for_model(self.config_model),
            "default_config": self.config_model().model_dump(
                mode="json", by_alias=True
            ),
        }


def _config_env_key(server_name: str, config_model: type) -> str:
    """Derive env var key: UNIQUE_MCP_TOOL_{SERVER}_{CONFIG}_CONFIG.

    Example: ``mcp-search`` + ``SearchToolConfig``
    → ``UNIQUE_MCP_TOOL_MCP_SEARCH_SEARCH_TOOL_CONFIG``
    """
    server_part = re.sub(r"[-\s]", "_", server_name).upper()
    config_name = re.sub(r"Config$", "", config_model.__name__)
    config_snake = re.sub(r"(?<!^)(?=[A-Z])", "_", config_name).upper()
    return f"UNIQUE_MCP_TOOL_{server_part}_{config_snake}_CONFIG"


def get_tool_config(config_model: type[_T]) -> _T:
    """Dependency factory — resolves and validates tool config.

    Lookup order:
      1. ``_meta[CONFIG_META_KEY]`` — injected by host at callTool time
      2. ``UNIQUE_MCP_TOOL_{SERVER}_{CONFIG}_CONFIG`` env var — dev/CI override
      3. ``config_model`` defaults

    Use as a default value in tool signatures::

        config: MyConfig = get_tool_config(MyConfig)
    """
    from unique_mcp.unique_injectors import get_request_meta  # avoid circular

    def _inner(server: Any = CurrentFastMCP()) -> _T:
        raw = (get_request_meta() or {}).get(CONFIG_META_KEY)
        if raw is not None:
            if isinstance(raw, str):
                return config_model.model_validate_json(raw)
            return config_model.model_validate(raw)

        env_key = _config_env_key(server.name, config_model)
        env_val = os.environ.get(env_key)
        if env_val:
            return config_model.model_validate_json(env_val)

        return config_model()

    return Depends(_inner)  # type: ignore[return-value]


__all__ = [
    "ConfigSchemaMeta",
    "get_tool_config",
]
