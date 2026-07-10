"""V2 WebSearch mode strategy: AI-planned multi-step research."""

from __future__ import annotations

from typing import cast

from jinja2 import Template
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
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
from unique_web_search.services.executors.v2.config import WebSearchV2Config
from unique_web_search.services.executors.v2.executor import WebSearchV2Executor
from unique_web_search.services.executors.v2.schema import WebSearchPlan
from unique_web_search.services.search_engine import resolve_search_engine_mode


class WebSearchV2Strategy(WebSearchModeStrategy):
    def __init__(self, mode_config: WebSearchV2Config) -> None:
        self.mode_config = mode_config

    def build_tool_parameters(
        self, ctx: WebSearchToolContext
    ) -> WebSearchToolParametersType:
        """Build the V2 plan schema shaped for the active search-engine mode."""
        return WebSearchPlan.with_search_engine_mode(
            resolve_search_engine_mode(ctx.search_engine_config)
        )

    def tool_description(self, ctx: WebSearchToolContext) -> str:
        """Return the static V2 tool description from mode config."""
        return self.mode_config.tool_description

    def system_prompt(self, ctx: WebSearchToolContext) -> str:
        """Render the V2 Jinja system prompt with plan examples and schema hint."""
        engine_mode = resolve_search_engine_mode(ctx.search_engine_config)
        return Template(self.mode_config.tool_description_for_system_prompt).render(
            max_steps=self.mode_config.max_steps,
            date_string=ctx.date_string,
            search_engine_mode=engine_mode.value,
            tool_parameters_schema=WebSearchPlan.schema_hint(engine_mode),
            example_simple=WebSearchPlan.build_example_simple(
                engine_mode
            ).model_dump_json(indent=2),
            example_complex=WebSearchPlan.build_example_complex(
                engine_mode
            ).model_dump_json(indent=2),
        )

    def build_executor(
        self,
        *,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        parameters: WebSearchToolParametersInstance,
        exposed_params_cls: type[ExposedParams] | None,
    ) -> WebSearchV2Executor:
        """Construct the V2 executor with the configured max-steps budget."""
        return WebSearchV2Executor(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=cast(WebSearchPlan, parameters),
            max_steps=self.mode_config.max_steps,
            exposed_params_cls=exposed_params_cls,
        )
