"""V1 WebSearch mode strategy: single-query search with optional refinement."""

from __future__ import annotations

from typing import cast

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
from unique_web_search.services.executors.v1.config import WebSearchV1Config
from unique_web_search.services.executors.v1.executor import WebSearchV1Executor
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters


class WebSearchV1Strategy(WebSearchModeStrategy):
    def __init__(self, mode_config: WebSearchV1Config) -> None:
        self.mode_config = mode_config

    def build_tool_parameters(
        self, ctx: WebSearchToolContext
    ) -> WebSearchToolParametersType:
        return WebSearchToolParameters.with_exposed_fields(
            build_exposed_tool_field_defs(ctx.search_engine_config),
            query_description=self.mode_config.tool_parameters_description.query_description,
        )

    def tool_description(self, ctx: WebSearchToolContext) -> str:
        return self.mode_config.tool_description

    def system_prompt(self, ctx: WebSearchToolContext) -> str:
        return self.mode_config.tool_description_for_system_prompt

    def build_executor(
        self,
        *,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        parameters: WebSearchToolParametersInstance,
    ) -> WebSearchV1Executor:
        refine_query_mode = self.mode_config.refine_query_mode
        return WebSearchV1Executor(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=cast(WebSearchToolParameters, parameters),
            refine_query_system_prompt=refine_query_mode.system_prompt,
            refine_query_language_model=refine_query_mode.language_model,
            mode=refine_query_mode.mode,
            max_queries=self.mode_config.max_queries,
        )
