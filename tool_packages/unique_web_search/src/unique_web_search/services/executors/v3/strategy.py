"""V3 WebSearch mode strategy: agent-driven search + on-demand page reads."""

from __future__ import annotations

import re
from typing import cast

from jinja2 import Template
from unique_search_proxy_core.search_engines.call_schema import (
    build_exposed_tool_field_defs,
)
from unique_toolkit.language_model import LanguageModelFunction

from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.modes import (
    WebSearchModeStrategy,
    WebSearchToolContext,
    WebSearchToolParametersInstance,
    WebSearchToolParametersType,
)
from unique_web_search.services.executors.v3.config import WebSearchV3Config
from unique_web_search.services.executors.v3.executor import WebSearchV3Executor
from unique_web_search.services.executors.v3.schema import (
    Command,
    WebSearchV3ToolParameters,
)

_DISPLAY_NAME_SUFFIX = {
    Command.SEARCH: " - Searching",
    Command.FETCH_URLS: " - Reading Pages",
}


class WebSearchV3Strategy(WebSearchModeStrategy):
    def __init__(self, mode_config: WebSearchV3Config) -> None:
        self.mode_config = mode_config

    def build_tool_parameters(
        self, ctx: WebSearchToolContext
    ) -> WebSearchToolParametersType:
        exposed_defs = build_exposed_tool_field_defs(ctx.search_engine_config)
        return WebSearchV3ToolParameters.with_exposed_fields(exposed_defs)

    def tool_description(self, ctx: WebSearchToolContext) -> str:
        exposed_defs = build_exposed_tool_field_defs(ctx.search_engine_config)
        return Template(self.mode_config.tool_description).render(
            tool_parameters_schema=WebSearchV3ToolParameters.schema_hint(
                exposed_defs,
            ),
        )

    def system_prompt(self, ctx: WebSearchToolContext) -> str:
        return Template(self.mode_config.tool_description_for_system_prompt).render(
            date_string=ctx.date_string,
        )

    def format_information_for_system_prompt(self, *, default: str) -> str:
        return self.mode_config.tool_format_information_for_system_prompt

    def build_executor(
        self,
        *,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        parameters: WebSearchToolParametersInstance,
    ) -> WebSearchV3Executor:
        return WebSearchV3Executor(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=cast(WebSearchV3ToolParameters, parameters),
        )

    def build_display_name(
        self,
        *,
        base_display_name: str,
        parameters: WebSearchToolParametersInstance,
    ) -> str:
        parameters = cast(WebSearchV3ToolParameters, parameters)
        # Drop the standalone word "search" (case-insensitive) so the phase
        # suffix reads cleanly, e.g. "Web Search" + " - Reading Pages".
        display_name = re.sub(
            r"\bsearch\b", "", base_display_name, flags=re.IGNORECASE
        ).strip()
        suffix = _DISPLAY_NAME_SUFFIX.get(parameters.command)
        if suffix is None:
            raise ValueError(f"Invalid command: {parameters.command}")
        return display_name + suffix
