from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, AsyncIterator, Generic, TypeVar

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.agent_engines.output_schema import AgentSearchOutput
from unique_search_proxy_core.schema import (
    AgentSearchResponse,
    AgentSearchStreamEvent,
    camelized_model_config,
)

if TYPE_CHECKING:
    from httpx import AsyncClient

T = TypeVar("T", bound="AgentEngineType")
AgentRequestT = TypeVar("AgentRequestT", bound=BaseModel)


# Default agent generation instructions. Kept aligned with
# unique_web_search.services.search_engine.utils.grounding.models.GENERATION_INSTRUCTIONS
DEFAULT_GENERATION_INSTRUCTIONS = """You are an Expert Web Research Agent whose goal is to extract the MAXIMUM amount of detail from every source you find.

## Core Directives
1. **Search broadly** — issue multiple searches with varied keywords and phrasings to cover every angle of the query.
2. **Read every source thoroughly** — do NOT skim. Extract every relevant fact, figure, statistic, date, name, quote, and piece of context.
3. **One entry per source** — each source gets its own result object. Never merge information from different sources into a single entry.
4. **Preserve detail** — prefer verbosity over brevity. Include specific numbers, full names, exact dates, and direct quotes whenever available. Do NOT paraphrase away precision.
5. **No omissions** — if a source contains relevant information, it MUST appear in your output. When in doubt, include it.
"""


class AgentEngineType(StrEnum):
    """Registered agent search engine ids (JSON discriminator values)."""

    BING = "bing"
    VERTEXAI = "vertexai"


class BaseAgentEngineConfig(BaseModel, Generic[T]):
    """Shared agent-engine config; each engine narrows ``engine`` with a Literal."""

    model_config = camelized_model_config

    engine: T
    generation_instructions: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=10,
        ),
    ] = Field(
        default=DEFAULT_GENERATION_INSTRUCTIONS,
        description="Instructions injected into the grounding agent.",
    )
    output_schema: SkipJsonSchema[type[BaseModel]] = Field(
        default=AgentSearchOutput,
        exclude=True,
        description=(
            "Pydantic model defining the structured JSON shape the agent must return."
        ),
    )
    timeout: int = Field(
        default=120,
        ge=1,
        le=600,
        description="Request timeout in seconds (agent runs can be slow).",
    )


class AgentSearchEngine(ABC, Generic[AgentRequestT]):
    """Agent (grounded) search engine contract for v1 providers.

    Implementations call the upstream agent/grounding provider and return opaque
    ``answer`` text plus ``raw`` provider payload. Content resolution is left to
    consumers; this layer stays provider-egress only.
    """

    engine_id: str

    def __init__(
        self,
        *,
        http_client: AsyncClient | None = None,
    ) -> None:
        self._http_client = http_client

    @property
    @abstractmethod
    def mode(self) -> str:
        """Provider mode identifier for observability (always ``agent``)."""

    @abstractmethod
    async def search(self, request: AgentRequestT) -> AgentSearchResponse:
        """Run a grounded search and return the assembled response."""

    @abstractmethod
    def stream(
        self,
        request: AgentRequestT,
    ) -> AsyncIterator[AgentSearchStreamEvent]:
        """Yield incremental events, terminating with an ``AgentSearchDone``."""
