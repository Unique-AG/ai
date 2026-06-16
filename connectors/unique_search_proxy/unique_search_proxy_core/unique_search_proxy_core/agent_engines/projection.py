from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field

from unique_search_proxy_core.model_derivation import derive_request_model
from unique_search_proxy_core.param_policy import QUERY_FIELD

_AGENT_REQUEST_EXCLUDED_FIELDS = frozenset({"output_schema"})


def _agent_request_model_name(config_cls: type[BaseModel]) -> str:
    """``BingAgentConfig`` -> ``BingAgentSearchRequest``."""
    base = config_cls.__name__
    if base.endswith("Config"):
        base = base[: -len("Config")]
    if base.endswith("Agent"):
        return f"{base}SearchRequest"
    return f"{base}AgentSearchRequest"


@lru_cache(maxsize=32)
def build_agent_request_model(config_cls: type[BaseModel]) -> type[BaseModel]:
    """Derive ``POST /v1/agent-search`` body: ``query`` + all config fields."""
    return derive_request_model(
        config_cls,
        leading_fields=(
            (
                QUERY_FIELD,
                (
                    str,
                    Field(
                        ...,
                        min_length=1,
                        description="Search query string",
                    ),
                ),
            ),
        ),
        model_name=_agent_request_model_name,
        exclude_fields=_AGENT_REQUEST_EXCLUDED_FIELDS,
        unwrap_exposable_params=False,
    )


__all__ = ["build_agent_request_model"]
