"""Compose the LLM-facing tool-parameter schema for each WebSearch mode.

``WebSearchTool.tool_description`` needs, per configured mode, both the Pydantic
model describing the tool-call arguments and the rendered tool-description text.
The per-mode wiring differs:

* V1 folds the engine's ``expose=True`` params into a flat query schema.
* V2 tailors its research-plan schema to the resolved search-engine mode.
* V3 folds exposed params into the schema and inlines that schema into its
  description template.

Keeping this composition here leaves the tool class free of schema-building
detail.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from jinja2 import Template
from pydantic import BaseModel
from unique_search_proxy_core.search_engines.call_schema import (
    build_exposed_tool_field_defs,
)

from unique_web_search.services.executors.base_config import WebSearchMode
from unique_web_search.services.executors.v1.config import WebSearchV1Config
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.executors.v2.config import WebSearchV2Config
from unique_web_search.services.executors.v2.schema import WebSearchPlan
from unique_web_search.services.executors.v3.config import WebSearchV3Config
from unique_web_search.services.executors.v3.schema import WebSearchV3ToolParameters
from unique_web_search.services.search_engine.base import SearchEngineMode

__all__ = ["ComposedToolParameters", "compose_tool_parameters"]

WebSearchModeConfig = WebSearchV1Config | WebSearchV2Config | WebSearchV3Config
ToolParametersModel = (
    type[WebSearchToolParameters]
    | type[WebSearchPlan]
    | type[WebSearchV3ToolParameters]
)


@dataclass(frozen=True)
class ComposedToolParameters:
    """Tool-call schema and description for a single configured WebSearch mode."""

    parameters: ToolParametersModel
    description: str


def compose_tool_parameters(
    mode_config: WebSearchModeConfig,
    *,
    search_engine_config: BaseModel,
    resolve_search_engine_mode: Callable[[], SearchEngineMode],
) -> ComposedToolParameters:
    """Build the tool-call schema and description for the configured mode.

    ``resolve_search_engine_mode`` is invoked lazily and only for V2, whose plan
    schema depends on the search-engine mode; V1/V3 derive their schema from the
    engine's exposed params instead.
    """
    match mode_config.mode:
        case WebSearchMode.V1:
            return _compose_v1(
                cast(WebSearchV1Config, mode_config), search_engine_config
            )
        case WebSearchMode.V3:
            return _compose_v3(
                cast(WebSearchV3Config, mode_config), search_engine_config
            )
        case _:
            return _compose_v2(
                cast(WebSearchV2Config, mode_config), resolve_search_engine_mode()
            )


def _compose_v1(
    mode_config: WebSearchV1Config,
    search_engine_config: BaseModel,
) -> ComposedToolParameters:
    parameters = WebSearchToolParameters.with_exposed_fields(
        build_exposed_tool_field_defs(search_engine_config),
        query_description=mode_config.tool_parameters_description.query_description,
    )
    return ComposedToolParameters(
        parameters=parameters,
        description=mode_config.tool_description,
    )


def _compose_v2(
    mode_config: WebSearchV2Config,
    search_engine_mode: SearchEngineMode,
) -> ComposedToolParameters:
    parameters = WebSearchPlan.with_search_engine_mode(search_engine_mode)
    return ComposedToolParameters(
        parameters=parameters,
        description=mode_config.tool_description,
    )


def _compose_v3(
    mode_config: WebSearchV3Config,
    search_engine_config: BaseModel,
) -> ComposedToolParameters:
    exposed_field_defs = build_exposed_tool_field_defs(search_engine_config)
    parameters = WebSearchV3ToolParameters.with_exposed_fields(exposed_field_defs)
    description = Template(mode_config.tool_description).render(
        tool_parameters_schema=WebSearchV3ToolParameters.schema_hint(
            exposed_field_defs
        ),
    )
    return ComposedToolParameters(parameters=parameters, description=description)
