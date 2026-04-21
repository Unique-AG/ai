"""Structured LLM output for the V3 search-outcome judge."""

from pydantic import Field
from unique_toolkit._common.utils.structured_output.schema import (
    StructuredOutputModel,
)


class V3SearchOutcomeJudgeResult(StructuredOutputModel):
    """Verdict on whether SERP snippets satisfy the objective and what to do next."""

    url_indices_to_fetch: list[int] = Field(
        description="List of indices of results to fetch. Empty if none are useful.",
    )
    suggested_follow_up_queries: list[str] = Field(
        description="List of potential follow-up queries to meet the objective.",
    )
    rationale: str = Field(
        description="Short justification for the above decisions.",
    )
