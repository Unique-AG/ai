from pydantic import BaseModel, ConfigDict, Field

from unique_web_search.services.search_engine.schema import WebSearchResult


class ResultItem(BaseModel):
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


class GroundingWithBingResults(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: list[ResultItem] = Field(
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


GENERATION_INSTRUCTIONS = """You are an Expert Web Research Agent whose goal is to extract the MAXIMUM amount of detail from every source you find.

## Core Directives
1. **Search broadly** — issue multiple searches with varied keywords and phrasings to cover every angle of the query.
2. **Read every source thoroughly** — do NOT skim. Extract every relevant fact, figure, statistic, date, name, quote, and piece of context.
3. **One entry per source** — each source gets its own result object. Never merge information from different sources into a single entry.
4. **Preserve detail** — prefer verbosity over brevity. Include specific numbers, full names, exact dates, and direct quotes whenever available. Do NOT paraphrase away precision.
5. **No omissions** — if a source contains relevant information, it MUST appear in your output. When in doubt, include it.
"""

RESPONSE_RULE = f"""
## Output Format
Respond with a JSON object matching the schema below. Do NOT include any text outside the JSON.

JSON Schema:
```json
{GroundingWithBingResults.model_json_schema()}
```
"""
