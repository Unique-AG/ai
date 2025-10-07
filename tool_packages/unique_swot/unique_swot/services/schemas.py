"""
SWOT Analysis Data Schemas

This module defines the core data structures used throughout the SWOT analysis system.
These schemas represent the workflow from planning to execution, including data sources,
analysis steps, and results.
"""

from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from unique_swot.services.generation import (
    SWOTAnalysisModels,
    SWOTComponent,
)

# Type definitions for SWOT operations
SWOTOperation = Literal["generate", "modify", "retrieve"]
TStep = TypeVar("TStep", bound="PlannedSWOTStep")


class SourceType(StrEnum):
    """Enumeration of supported data source types for SWOT analysis."""

    WEB_SEARCH = "web_search"
    INTERNAL_DOCUMENT = "internal_document"
    EARNINGS_CALL = "earnings_call"


class Source(BaseModel):
    """
    Represents a data source used in SWOT analysis.

    Attributes:
        source_id: Unique identifier for the source
        type: The type of data source (web search, internal document, etc.)
        content: The actual content/text from the source
    """

    type: SourceType
    source_id: str
    content: str


class PlannedSWOTStep(BaseModel):
    """
    Represents a single step in a SWOT analysis plan.

    This is the schema that the LLM will use when generating SWOT analysis plans.
    Each step defines what SWOT component to analyze and what operation to perform.

    Attributes:
        component: The SWOT component to analyze (Strengths, Weaknesses, Opportunities, Threats)
        operation: The operation to perform (generate new analysis or modify existing)
        modify_instruction: Optional custom instruction for modify operations
    """

    model_config = ConfigDict(extra="forbid")

    component: SWOTComponent
    operation: SWOTOperation
    modify_instruction: str | None = Field(
        description="Custom instruction for the modify operation. This is only used if the operation is modify."
    )


class ExecutedSwotStep(PlannedSWOTStep):
    """
    Represents a SWOT analysis step that has been executed with results.

    Extends SWOTStep to include the actual analysis results. This is used to track
    completed steps in the SWOT analysis workflow.

    Attributes:
        result: The generated SWOT analysis results for this step
    """

    result: SWOTAnalysisModels

    @classmethod
    def from_step_and_result(
        cls, *, step: PlannedSWOTStep, result: SWOTAnalysisModels
    ) -> "ExecutedSwotStep":
        """
        Factory method to create an ExecutedSwotStep from a plan step and its results.

        Args:
            step: The original SWOT step from the plan
            result: The analysis results generated for this step

        Returns:
            ExecutedSwotStep with the step details and results
        """
        return cls(
            component=step.component,
            operation=step.operation,
            modify_instruction=step.modify_instruction,
            result=result,
        )


class SWOTPlanBase(BaseModel, Generic[TStep]):
    """
    Base class for SWOT analysis plans.

    This generic base class allows for both planned steps (SWOTStep) and executed steps
    (ExecutedSwotStep) to be used in the same plan structure.

    Attributes:
        objective: The overall objective/goal of the SWOT analysis
        steps: List of steps to execute in the analysis
    """

    model_config = ConfigDict(extra="forbid")
    objective: str = Field(description="The objective that the user wants to achieve")
    steps: list[TStep]


class SWOTPlan(SWOTPlanBase[PlannedSWOTStep]):
    """
    Represents a planned SWOT analysis before execution.

    This schema is used when the LLM generates a plan for SWOT analysis.
    It contains the objective and the steps to be executed, but no results yet.
    """

    def validate_swot_plan(self) -> None:
        """
        Validates a SWOT analysis plan.

        Args:
            plan: The SWOT analysis plan to validate
        """
        for step in self.steps:
            if step.operation == "modify" and step.modify_instruction is None:
                raise ValueError("Modify instruction is required for modify operation")


class ExecutedSWOTPlan(SWOTPlanBase[ExecutedSwotStep]):
    """
    Represents a SWOT analysis plan that has been executed with results.

    This schema is used to track the completed SWOT analysis workflow,
    including all executed steps and their corresponding results.
    """

    ...
