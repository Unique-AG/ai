from enum import StrEnum
from typing import Literal, overload

from pydantic import Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel
from unique_toolkit.language_model import (
    LanguageModelName,
)
from unique_toolkit.language_model.builder import MessagesBuilder

RESTRICT_DATE_DESCRIPTION = """
Restricts results to a recent time window. Format: `[period][number]` — `d`=days, `w`=weeks, `m`=months, `y`=years.  
Examples: `d1` (24h), `w1` (1 week), `m3` (3 months), `y1` (1 year).  
Omit for no date filter. Avoid adding date terms in the main query.
"""

REFINE_QUERY_SYSTEM_PROMPT = """
You're task consist of a query for a search engine.

** Refine the query Guidelines **
- The query should be a string that does not exceed 6 key words.
- Never include temporal information in the refined query. There is a separate field for this purpose.
- You may add the additional advanced syntax when relevant to refine the results:
- Use quotes `"..."` for exact words (avoid doing it for phrases as it will dramatically reduce the number of results).
- Use `-word` to exclude terms.
- Use `site:domain.com` to restrict to a site.
- Use `intitle:`, `inurl:` to target title/URL.
- Use `OR` for alternatives, `*` as a wildcard.
- Use `..` for number ranges (e.g., 2010..2020).
- Use `AROUND(N)` to find terms close together.
- Use `define:word` for definitions.
- Combine operators for powerful filtering.

** IMPORTANT **
- You should not use any date restriction in the refined query.
""".strip()


class RefineQueryMode(StrEnum):
    ADVANCED = "advanced"
    BASIC = "basic"


class RefinedQuery(StructuredOutputModel):
    """A refined query."""

    refined_query: str = Field(
        description="The refined query optimized for the search engine."
    )
    restrict_date: str | None = Field(description=RESTRICT_DATE_DESCRIPTION)


class RefinedQueries(StructuredOutputModel):
    """A refined query."""

    refined_queries: list[RefinedQuery] = Field(
        description="The refined queries optimized for the search engine."
    )


@overload
async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LanguageModelName,
    mode: Literal[RefineQueryMode.BASIC],
) -> RefinedQueries: ...


@overload
async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LanguageModelName,
    mode: Literal[RefineQueryMode.ADVANCED],
) -> RefinedQuery: ...


async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LanguageModelName,
    mode: RefineQueryMode,
) -> RefinedQuery | RefinedQueries:
    """Refine the query to be more specific and relevant to the user's question."""
    messages = (
        MessagesBuilder()
        .system_message_append(REFINE_QUERY_SYSTEM_PROMPT)
        .user_message_append(query)
        .build()
    )
    
    if mode == RefineQueryMode.BASIC:
        structured_output_model = RefinedQueries
    else:
        structured_output_model = RefinedQuery

    response = await language_model_service.complete_async(
        messages,
        model_name=language_model.name,
        structured_output_model=structured_output_model,
        structured_output_enforce_schema=True,
    )

    parsed_response = response.choices[0].message.parsed
    if parsed_response is None:
        raise ValueError("Failed to parse insights from LLM response")

    return structured_output_model.model_validate(parsed_response)
