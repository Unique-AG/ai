import pytest

from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.schemas import (
    SWOTOperation,
    SWOTPlan,
    SWOTResult,
    SWOTStepPlan,
)


def _build_plan(
    strengths_op=SWOTOperation.GENERATE,
    weaknesses_op=SWOTOperation.GENERATE,
    opportunities_op=SWOTOperation.GENERATE,
    threats_op=SWOTOperation.GENERATE,
    strengths_instruction=None,
):
    return SWOTPlan(
        objective="Test objective",
        strengths=SWOTStepPlan(
            operation=strengths_op, modify_instruction=strengths_instruction
        ),
        weaknesses=SWOTStepPlan(operation=weaknesses_op, modify_instruction=None),
        opportunities=SWOTStepPlan(operation=opportunities_op, modify_instruction=None),
        threats=SWOTStepPlan(operation=threats_op, modify_instruction=None),
    )


def test_validate_swot_plan_requires_instruction_for_modify():
    plan = _build_plan(strengths_op=SWOTOperation.MODIFY)

    with pytest.raises(ValueError):
        plan.validate_swot_plan()


def test_plan_len_counts_requested_components():
    plan = _build_plan(threats_op=SWOTOperation.NOT_REQUESTED)
    assert len(plan) == 3


def test_swot_result_assignment_and_to_markdown():
    plan = _build_plan()
    result = SWOTResult.init_from_plan(plan=plan)

    result.assign_result(SWOTComponent.STRENGTHS, "Strong brand")
    result.assign_result(SWOTComponent.THREATS, "New entrants")

    assert result.strengths.result == "Strong brand"
    assert result.threats.result == "New entrants"

    markdown = result.to_markdown_report(
        markdown_jinja_template="{{ strengths.result }} | {{ threats.result }}",
        processor=str.upper,
    )
    assert markdown == "STRONG BRAND | NEW ENTRANTS"
