"""Data schemas for the Write-Up Agent."""

from typing import Any

from pydantic import BaseModel, Field


class GroupData(BaseModel):
    """
    Represents a group of rows from a DataFrame.

    This is the core data structure passed between handlers in the pipeline.
    """

    group_key: str = Field(
        ...,
        description="The value of the grouping column for this group (e.g., 'Introduction', 'Methods')",
    )

    rows: list[dict[str, Any]] = Field(
        ...,
        description="List of row dictionaries containing the selected columns for this group",
    )


class ProcessedGroup(GroupData):
    """
    Represents a group after LLM processing.

    Extends GroupData with the LLM-generated response.
    """

    llm_response: str = Field(
        ...,
        description="The LLM-generated summary/output for this group",
    )
