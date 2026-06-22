"""Default structured-output models for agent search engines.

Kept aligned with
``unique_web_search.services.search_engine.utils.grounding.models.GroundingSearchResults``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from unique_search_proxy_core.schema import WebSearchResult


class AgentSearchOutputResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str = Field(
        description="The URL of the source this information was extracted from.",
    )
    source_title: str = Field(
        description="The title or headline of the source page.",
    )
    detailed_answer: str = Field(
        description=(
            "A comprehensive, in-depth answer derived from this single source. "
            "Include every relevant fact, figure, statistic, date, name, quote, "
            "and contextual detail found in the source. Do NOT summarize — "
            "preserve as much of the original information as possible."
        ),
    )
    key_facts: list[str] = Field(
        description=(
            "A list of discrete, standalone facts extracted from this source. "
            "Each fact should be specific and self-contained (e.g. include names, "
            "numbers, dates, outcomes)."
        ),
    )


class AgentSearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[AgentSearchOutputResultItem] = Field(
        description=(
            "One entry per source. Every source found must be represented. "
            "Do not merge or skip sources."
        ),
    )

    def to_web_search_results(self) -> list[WebSearchResult]:
        return [
            WebSearchResult(
                url=result.source_url,
                title=result.source_title,
                snippet="\n".join(result.key_facts),
                content=result.detailed_answer,
            )
            for result in self.results
        ]


__all__ = ["AgentSearchOutput", "AgentSearchOutputResultItem"]
