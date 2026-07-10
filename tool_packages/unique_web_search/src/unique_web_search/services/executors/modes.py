"""Per-mode strategy objects for the WebSearch tool.

Each WebSearch mode (V1/V2/V3) differs only in how it builds its LLM-facing
surface and which executor runs it. A :class:`WebSearchModeStrategy` owns all of
that per-mode behaviour in one place:

- the tool-call parameter model (``query`` plus any engine-exposed knobs),
- the tool description shown to the model,
- the system-prompt text and citation/format-information text,
- the executor construction, and
- the runtime display name.

``WebSearchTool`` resolves the strategy for the active mode via
:func:`get_mode_strategy` and delegates to it, staying free of mode branching.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from pydantic import BaseModel
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_toolkit.language_model import LanguageModelFunction

from unique_web_search.services.executors.base_config import WebSearchMode
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.v1.config import WebSearchV1Config
from unique_web_search.services.executors.v1.executor import WebSearchV1Executor
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.executors.v2.config import WebSearchV2Config
from unique_web_search.services.executors.v2.executor import WebSearchV2Executor
from unique_web_search.services.executors.v2.schema import WebSearchPlan
from unique_web_search.services.executors.v3.config import WebSearchV3Config
from unique_web_search.services.executors.v3.executor import WebSearchV3Executor
from unique_web_search.services.executors.v3.schema import WebSearchV3ToolParameters

__all__ = [
    "WebSearchExecutor",
    "WebSearchModeConfig",
    "WebSearchModeStrategy",
    "WebSearchToolContext",
    "WebSearchToolParametersInstance",
    "WebSearchToolParametersType",
    "get_mode_strategy",
]

WebSearchModeConfig = WebSearchV1Config | WebSearchV2Config | WebSearchV3Config

WebSearchToolParametersType = (
    type[WebSearchToolParameters]
    | type[WebSearchPlan]
    | type[WebSearchV3ToolParameters]
)

WebSearchToolParametersInstance = (
    WebSearchToolParameters | WebSearchPlan | WebSearchV3ToolParameters
)

WebSearchExecutor = WebSearchV1Executor | WebSearchV2Executor | WebSearchV3Executor

_STRATEGY_FACTORIES: (
    dict[WebSearchMode, Callable[[WebSearchModeConfig], WebSearchModeStrategy]]
    | None
) = None


@dataclass(frozen=True)
class WebSearchToolContext:
    """Inputs the mode strategy needs to build the LLM-facing tool surface.

    ``exposed_params_cls`` is resolved once by ``WebSearchTool`` at init so
    strategies do not re-call ``exposed_params_model()``. The engine *mode*
    (standard vs agent) is resolved lazily by the one strategy (V2) that needs
    it, so V1/V3 never pay for a resolution they ignore.
    """

    search_engine_config: BaseModel
    date_string: str
    exposed_params_cls: type[ExposedParams] | None


class WebSearchModeStrategy(ABC):
    """Mode-specific behaviour for building and running the WebSearch tool."""

    @abstractmethod
    def build_tool_parameters(
        self, ctx: WebSearchToolContext
    ) -> WebSearchToolParametersType:
        """Build the tool-call parameter model (``query`` plus exposed knobs)."""

    @abstractmethod
    def tool_description(self, ctx: WebSearchToolContext) -> str:
        """Return the description the model sees when choosing this tool."""

    @abstractmethod
    def system_prompt(self, ctx: WebSearchToolContext) -> str:
        """Return the tool's system-prompt instructions."""

    @abstractmethod
    def build_executor(
        self,
        *,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        parameters: WebSearchToolParametersInstance,
        exposed_params_cls: type[ExposedParams] | None,
    ) -> WebSearchExecutor:
        """Construct the executor that runs a validated tool call."""

    def format_information_for_system_prompt(self, *, default: str) -> str:
        """Return citation/format instructions; falls back to the tool default."""
        return default

    def build_display_name(
        self,
        *,
        base_display_name: str,
        parameters: WebSearchToolParametersInstance,
    ) -> str:
        """Return the runtime display name for a tool call."""
        return base_display_name


def _strategy_factories() -> dict[
    WebSearchMode, Callable[[WebSearchModeConfig], WebSearchModeStrategy]
]:
    global _STRATEGY_FACTORIES
    if _STRATEGY_FACTORIES is None:
        from unique_web_search.services.executors.v1.strategy import (
            WebSearchV1Strategy,
        )
        from unique_web_search.services.executors.v2.strategy import (
            WebSearchV2Strategy,
        )
        from unique_web_search.services.executors.v3.strategy import (
            WebSearchV3Strategy,
        )

        _STRATEGY_FACTORIES = {
            WebSearchMode.V1: lambda cfg: WebSearchV1Strategy(
                cast(WebSearchV1Config, cfg),
            ),
            WebSearchMode.V2: lambda cfg: WebSearchV2Strategy(
                cast(WebSearchV2Config, cfg),
            ),
            WebSearchMode.V3: lambda cfg: WebSearchV3Strategy(
                cast(WebSearchV3Config, cfg),
            ),
        }
    return _STRATEGY_FACTORIES


def get_mode_strategy(mode_config: WebSearchModeConfig) -> WebSearchModeStrategy:
    """Resolve the strategy for the configured WebSearch mode."""
    factory = _strategy_factories()[mode_config.mode]
    return factory(mode_config)
