"""Tests for SWOT analysis data schemas."""

import pytest

from unique_swot.services.generation import SWOTComponent
from unique_swot.services.schemas import (
    SWOTOperation,
    SWOTPlan,
    SWOTResult,
    SWOTStepPlan,
    SWOTStepResult,
)


class TestSWOTOperation:
    """Test cases for SWOTOperation enum."""

    def test_swot_operation_values(self):
        """Test that SWOTOperation has expected values."""
        assert SWOTOperation.GENERATE == "generate"
        assert SWOTOperation.MODIFY == "modify"
        assert SWOTOperation.NOT_REQUESTED == "not_requested"

    def test_swot_operation_from_string(self):
        """Test creating SWOTOperation from string."""
        assert SWOTOperation("generate") == SWOTOperation.GENERATE
        assert SWOTOperation("modify") == SWOTOperation.MODIFY
        assert SWOTOperation("not_requested") == SWOTOperation.NOT_REQUESTED


class TestSWOTStepPlan:
    """Test cases for SWOTStepPlan class."""

    def test_swot_step_plan_generate_operation(self):
        """Test creating a SWOTStepPlan with generate operation."""
        step = SWOTStepPlan(
            operation=SWOTOperation.GENERATE,
            modify_instruction=None,
        )

        assert step.operation == SWOTOperation.GENERATE
        assert step.modify_instruction is None

    def test_swot_step_plan_modify_operation(self):
        """Test creating a SWOTStepPlan with modify operation."""
        step = SWOTStepPlan(
            operation=SWOTOperation.MODIFY,
            modify_instruction="Update with latest data",
        )

        assert step.operation == SWOTOperation.MODIFY
        assert step.modify_instruction == "Update with latest data"

    def test_swot_step_plan_not_requested_operation(self):
        """Test creating a SWOTStepPlan with not_requested operation."""
        step = SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED,
            modify_instruction=None,
        )

        assert step.operation == SWOTOperation.NOT_REQUESTED


class TestSWOTStepResult:
    """Test cases for SWOTStepResult class."""

    def test_swot_step_result_creation(self):
        """Test creating a SWOTStepResult."""
        result = SWOTStepResult(
            operation=SWOTOperation.GENERATE,
            modify_instruction=None,
            result="Generated SWOT analysis",
        )

        assert result.operation == SWOTOperation.GENERATE
        assert result.result == "Generated SWOT analysis"
        assert result.modify_instruction is None


class TestSWOTPlan:
    """Test cases for SWOTPlan class."""

    def test_swot_plan_creation(self, sample_swot_step_plan):
        """Test creating a valid SWOTPlan."""
        plan = SWOTPlan(
            objective="Analyze Company X",
            strengths=sample_swot_step_plan,
            weaknesses=sample_swot_step_plan,
            opportunities=sample_swot_step_plan,
            threats=sample_swot_step_plan,
        )

        assert plan.objective == "Analyze Company X"
        assert plan.strengths.operation == SWOTOperation.GENERATE
        assert plan.weaknesses.operation == SWOTOperation.GENERATE
        assert plan.opportunities.operation == SWOTOperation.GENERATE
        assert plan.threats.operation == SWOTOperation.GENERATE

    def test_swot_plan_validate_success(self, sample_swot_plan):
        """Test validating a correct SWOTPlan."""
        # Should not raise any exception
        sample_swot_plan.validate_swot_plan()

    def test_swot_plan_validate_modify_without_instruction(self):
        """Test that validation fails when modify operation lacks instruction."""
        plan = SWOTPlan(
            objective="Test",
            strengths=SWOTStepPlan(
                operation=SWOTOperation.MODIFY,
                modify_instruction=None,  # Missing instruction
            ),
            weaknesses=SWOTStepPlan(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
            ),
            opportunities=SWOTStepPlan(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
            ),
            threats=SWOTStepPlan(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
            ),
        )

        with pytest.raises(ValueError, match="Modify instruction is required"):
            plan.validate_swot_plan()

    def test_swot_plan_get_step_result_strengths(self, sample_swot_plan):
        """Test getting strengths step from plan."""
        step = sample_swot_plan.get_step_result(SWOTComponent.STRENGTHS)
        assert step == sample_swot_plan.strengths

    def test_swot_plan_get_step_result_weaknesses(self, sample_swot_plan):
        """Test getting weaknesses step from plan."""
        step = sample_swot_plan.get_step_result(SWOTComponent.WEAKNESSES)
        assert step == sample_swot_plan.weaknesses

    def test_swot_plan_get_step_result_opportunities(self, sample_swot_plan):
        """Test getting opportunities step from plan."""
        step = sample_swot_plan.get_step_result(SWOTComponent.OPPORTUNITIES)
        assert step == sample_swot_plan.opportunities

    def test_swot_plan_get_step_result_threats(self, sample_swot_plan):
        """Test getting threats step from plan."""
        step = sample_swot_plan.get_step_result(SWOTComponent.THREATS)
        assert step == sample_swot_plan.threats


class TestSWOTResult:
    """Test cases for SWOTResult class."""

    def test_swot_result_init_from_plan(self, sample_swot_plan):
        """Test creating SWOTResult from SWOTPlan."""
        result = SWOTResult.init_from_plan(plan=sample_swot_plan)

        assert result.objective == sample_swot_plan.objective
        assert result.strengths.operation == sample_swot_plan.strengths.operation
        assert result.weaknesses.operation == sample_swot_plan.weaknesses.operation
        assert (
            result.opportunities.operation == sample_swot_plan.opportunities.operation
        )
        assert result.threats.operation == sample_swot_plan.threats.operation

        # All results should be empty initially
        assert result.strengths.result == ""
        assert result.weaknesses.result == ""
        assert result.opportunities.result == ""
        assert result.threats.result == ""

    def test_swot_result_assign_result_strengths(self, sample_swot_plan):
        """Test assigning result to strengths."""
        result = SWOTResult.init_from_plan(plan=sample_swot_plan)
        result.assign_result(SWOTComponent.STRENGTHS, "Strong brand recognition")

        assert result.strengths.result == "Strong brand recognition"

    def test_swot_result_assign_result_weaknesses(self, sample_swot_plan):
        """Test assigning result to weaknesses."""
        result = SWOTResult.init_from_plan(plan=sample_swot_plan)
        result.assign_result(SWOTComponent.WEAKNESSES, "Limited market share")

        assert result.weaknesses.result == "Limited market share"

    def test_swot_result_assign_result_opportunities(self, sample_swot_plan):
        """Test assigning result to opportunities."""
        result = SWOTResult.init_from_plan(plan=sample_swot_plan)
        result.assign_result(SWOTComponent.OPPORTUNITIES, "Expanding into new markets")

        assert result.opportunities.result == "Expanding into new markets"

    def test_swot_result_assign_result_threats(self, sample_swot_plan):
        """Test assigning result to threats."""
        result = SWOTResult.init_from_plan(plan=sample_swot_plan)
        result.assign_result(SWOTComponent.THREATS, "Increasing competition")

        assert result.threats.result == "Increasing competition"

    def test_swot_result_assign_multiple_results(self, sample_swot_plan):
        """Test assigning results to multiple components."""
        result = SWOTResult.init_from_plan(plan=sample_swot_plan)

        result.assign_result(SWOTComponent.STRENGTHS, "Strength 1")
        result.assign_result(SWOTComponent.WEAKNESSES, "Weakness 1")
        result.assign_result(SWOTComponent.OPPORTUNITIES, "Opportunity 1")
        result.assign_result(SWOTComponent.THREATS, "Threat 1")

        assert result.strengths.result == "Strength 1"
        assert result.weaknesses.result == "Weakness 1"
        assert result.opportunities.result == "Opportunity 1"
        assert result.threats.result == "Threat 1"
