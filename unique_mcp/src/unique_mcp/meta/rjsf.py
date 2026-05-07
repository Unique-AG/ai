from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import BaseModel
from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model

from unique_mcp.meta.keys import CONFIG_SCHEMA_META_KEY


class ConfigSchemaMeta:
    """MetaPart that publishes RJSF schema at listTools time."""

    _META_KEY: ClassVar[str] = CONFIG_SCHEMA_META_KEY

    def __init__(
        self,
        config_model: type[BaseModel],
        *,
        key_transform: Callable[[str], str] | None = None,
    ) -> None:
        required = [
            name
            for name, field in config_model.model_fields.items()
            if field.is_required()
        ]
        if required:
            raise TypeError(
                f"{config_model.__name__} has required fields without defaults: "
                f"{required}. Every field in a ConfigSchemaMeta model must have a "
                "default so the host can build a starting config for the admin UI."
            )
        self.config_model = config_model
        self._key_transform = key_transform

    def merge_into_meta(self, meta: dict[str, Any]) -> None:
        key_transform = self._key_transform
        if key_transform is None:
            alias_gen = self.config_model.model_config.get("alias_generator")
            key_transform = alias_gen if callable(alias_gen) else None
        meta[self._META_KEY] = {
            "json_schema": self.config_model.model_json_schema(),
            "ui_schema": ui_schema_for_model(
                self.config_model,
                key_transform=key_transform,
            ),
            "default_config": self.config_model().model_dump(
                mode="json", by_alias=True
            ),
        }


__all__ = ["ConfigSchemaMeta"]
