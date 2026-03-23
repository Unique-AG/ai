from __future__ import annotations

import pytest
from pydantic import ValidationError

from unique_orchestrator.config import InputTokenDistributionConfig


class TestInputTokenDistributionConfigPercentForToolCallHistory:
    """Tests for the percent_for_tool_call_history field on InputTokenDistributionConfig."""

    @pytest.mark.ai
    def test_percent_for_tool_call_history__defaults_to_zero(self) -> None:
        """
        Purpose: Verify that the default value for percent_for_tool_call_history is 0.0,
        meaning tool call history reconstruction is disabled out of the box.

        Why this matters: New deployments must not incur the overhead of loading tool call
        history from the DB unless the operator explicitly opts in.

        Setup summary: Instantiate InputTokenDistributionConfig with no arguments and
        assert percent_for_tool_call_history == 0.0.
        """
        config = InputTokenDistributionConfig()

        assert config.percent_for_tool_call_history == 0.0

    @pytest.mark.ai
    def test_percent_for_tool_call_history__accepts_valid_fraction(self) -> None:
        """
        Purpose: Verify that a representative valid fraction (0 < v < 1) is accepted
        without raising a validation error.

        Why this matters: Operators need to set meaningful non-zero fractions such as 0.2
        to allocate token budget for historical tool call rounds.

        Setup summary: Instantiate with percent_for_tool_call_history=0.2 and assert the
        stored value equals 0.2.
        """
        config = InputTokenDistributionConfig(percent_for_tool_call_history=0.2)

        assert config.percent_for_tool_call_history == 0.2

    @pytest.mark.ai
    def test_percent_for_tool_call_history__accepts_zero(self) -> None:
        """
        Purpose: Verify that the boundary value 0.0 (disabled) is explicitly accepted.

        Why this matters: Zero is the sentinel value used to skip tool call history loading
        entirely; it must always be a valid configuration.

        Setup summary: Instantiate with percent_for_tool_call_history=0.0 and confirm
        no ValidationError is raised and the value is stored correctly.
        """
        config = InputTokenDistributionConfig(percent_for_tool_call_history=0.0)

        assert config.percent_for_tool_call_history == 0.0

    @pytest.mark.ai
    def test_percent_for_tool_call_history__rejects_value_of_one(self) -> None:
        """
        Purpose: Verify that a value of exactly 1.0 is rejected (constraint: lt=1.0).

        Why this matters: Allocating 100% of the input budget to tool call history would
        leave no tokens for the actual conversation, which is an invalid configuration.

        Setup summary: Attempt to instantiate with percent_for_tool_call_history=1.0 and
        assert that a ValidationError is raised.
        """
        with pytest.raises(ValidationError):
            InputTokenDistributionConfig(percent_for_tool_call_history=1.0)

    @pytest.mark.ai
    def test_percent_for_tool_call_history__rejects_value_above_one(self) -> None:
        """
        Purpose: Verify that values greater than 1.0 are rejected.

        Why this matters: A fraction above 1.0 has no meaningful interpretation as a
        percentage and indicates a misconfiguration.

        Setup summary: Attempt to instantiate with percent_for_tool_call_history=1.5 and
        assert that a ValidationError is raised.
        """
        with pytest.raises(ValidationError):
            InputTokenDistributionConfig(percent_for_tool_call_history=1.5)

    @pytest.mark.ai
    def test_percent_for_tool_call_history__rejects_negative_value(self) -> None:
        """
        Purpose: Verify that negative fractions are rejected (constraint: ge=0.0).

        Why this matters: A negative fraction is semantically meaningless as a token
        budget allocation; input validation should surface it as an error immediately.

        Setup summary: Attempt to instantiate with percent_for_tool_call_history=-0.1 and
        assert that a ValidationError is raised.
        """
        with pytest.raises(ValidationError):
            InputTokenDistributionConfig(percent_for_tool_call_history=-0.1)

    @pytest.mark.ai
    def test_percent_for_tool_call_history__accepts_max_valid_fraction(self) -> None:
        """
        Purpose: Verify that 0.99 (just below the upper limit) is accepted as a valid
        fraction.

        Why this matters: Edge values close to the constraint boundary are common sources
        of off-by-one bugs; explicit coverage prevents regressions.

        Setup summary: Instantiate with percent_for_tool_call_history=0.99 and confirm
        the value is stored without error.
        """
        config = InputTokenDistributionConfig(percent_for_tool_call_history=0.99)

        assert config.percent_for_tool_call_history == pytest.approx(0.99)
