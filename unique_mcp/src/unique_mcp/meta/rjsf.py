from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel
from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model

from unique_mcp.meta.keys import CONFIG_SCHEMA_META_KEY


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


__all__ = ["ConfigSchemaMeta"]
