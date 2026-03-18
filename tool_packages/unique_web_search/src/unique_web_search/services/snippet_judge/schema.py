"""Structured output schema for the snippet judge LLM.

Field order for SnippetJudgment: explanation first, then relevance_score (per plan).
"""

from pydantic import Field
from unique_toolkit._common.utils.structured_output.schema import (
    StructuredOutputModel,
)


class SnippetJudgment(StructuredOutputModel):
    """Per-result judgment: explanation and relevance score.

    Field order is explanation first, then relevance_score.
    """

    index: int = Field(
        ...,
        description="Zero-based index of the search result in the input list.",
    )
    explanation: str = Field(
        ...,
        description="Brief explanation of why this result is or is not relevant to the objective.",
    )
    relevance_score: float = Field(
        ...,
        description="Relevance score from 0.0 (not relevant) to 1.0 (highly relevant).",
        ge=0.0,
        le=1.0,
    )


class SnippetJudgeResponse(StructuredOutputModel):
    """Root structured output: one judgment per search result."""

    judgments: list[SnippetJudgment] = Field(
        ...,
        description="One judgment per search result, in the same order as the input list.",
    )
