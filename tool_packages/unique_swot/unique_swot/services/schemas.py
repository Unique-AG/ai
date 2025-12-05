"""
SWOT Analysis Data Schemas

This module defines the core data structures used throughout the SWOT analysis system.
These schemas represent the workflow from planning to execution, including data sources,
analysis steps, and results.
"""

from enum import StrEnum
from typing import Callable, Generic, TypeVar

from jinja2 import Template
from pydantic import BaseModel, Field

from unique_swot.services.generation.context import SWOTComponent


# Type definitions for SWOT operations
class SWOTOperation(StrEnum):
    GENERATE = "generate"
    MODIFY = "modify"
    NOT_REQUESTED = "not_requested"


class SWOTStepPlan(BaseModel):
    operation: SWOTOperation
    modify_instruction: str | None = Field(
        description="Custom instruction for the modify operation. This is only used if the operation is modify."
    )


class SWOTStepResult(SWOTStepPlan):
    result: str


TStep = TypeVar("TStep", bound=SWOTStepPlan)


class SWOT(BaseModel, Generic[TStep]):
    objective: str = Field(description="The objective of the plan to be executed")

    strengths: TStep = Field(description="The step to analyze the strengths")
    weaknesses: TStep = Field(description="The step to analyze the weaknesses")
    opportunities: TStep = Field(description="The step to analyze the opportunities")
    threats: TStep = Field(description="The step to analyze the threats")


class SWOTPlan(SWOT[SWOTStepPlan]):
    # from unique_swot.services.generation import SWOTComponent

    def validate_swot_plan(self) -> None:
        for step in [self.strengths, self.weaknesses, self.opportunities, self.threats]:
            if (
                step.operation == SWOTOperation.MODIFY
                and step.modify_instruction is None
            ):
                raise ValueError("Modify instruction is required for modify operations")

    def get_step_result(self, component: SWOTComponent) -> SWOTStepPlan:
        # from unique_swot.services.generation import SWOTComponent

        match component:
            case SWOTComponent.STRENGTHS:
                return self.strengths
            case SWOTComponent.WEAKNESSES:
                return self.weaknesses
            case SWOTComponent.OPPORTUNITIES:
                return self.opportunities
            case SWOTComponent.THREATS:
                return self.threats
            case _:
                raise ValueError(f"Invalid component: {component}")

    def __len__(self) -> int:
        return len(
            [
                step
                for step in [
                    self.strengths,
                    self.weaknesses,
                    self.opportunities,
                    self.threats,
                ]
                if step.operation != SWOTOperation.NOT_REQUESTED
            ]
        )


class SWOTResult(SWOT[SWOTStepResult]):
    # from unique_swot.services.generation import SWOTComponent

    @classmethod
    def init_from_plan(cls, *, plan: SWOTPlan) -> "SWOTResult":
        strengths_result = SWOTStepResult(
            operation=plan.strengths.operation,
            modify_instruction=plan.strengths.modify_instruction,
            result="",
        )
        weaknesses_result = SWOTStepResult(
            operation=plan.weaknesses.operation,
            modify_instruction=plan.weaknesses.modify_instruction,
            result="",
        )
        opportunities_result = SWOTStepResult(
            operation=plan.opportunities.operation,
            modify_instruction=plan.opportunities.modify_instruction,
            result="",
        )
        threats_result = SWOTStepResult(
            operation=plan.threats.operation,
            modify_instruction=plan.threats.modify_instruction,
            result="",
        )
        return cls(
            objective=plan.objective,
            strengths=strengths_result,
            weaknesses=weaknesses_result,
            opportunities=opportunities_result,
            threats=threats_result,
        )

    def assign_result(self, component: SWOTComponent, result: str) -> None:
        # from unique_swot.services.generation import SWOTComponent

        match component:
            case SWOTComponent.STRENGTHS:
                self.strengths.result = result
            case SWOTComponent.WEAKNESSES:
                self.weaknesses.result = result
            case SWOTComponent.OPPORTUNITIES:
                self.opportunities.result = result
            case SWOTComponent.THREATS:
                self.threats.result = result
            case _:
                raise ValueError(f"Invalid component: {component}")

    def to_markdown_report(
        self, markdown_jinja_template: str, processor: Callable[[str], str]
    ) -> str:
        report = Template(markdown_jinja_template).render(**self.model_dump())
        return processor(report)
