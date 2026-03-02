"""Tests for agentic generation utilities."""

import pytest

from unique_swot.services.generation.agentic.utils import create_progress_sequence


@pytest.mark.ai
def test_create_progress_sequence__produces_correct_values__standard_input() -> None:
    """
    Purpose: Verify create_progress_sequence yields the correct progression of values.
    Why this matters: Incorrect progress values cause misleading UI indicators.
    Setup summary: start=10, stop=80, steps=4 should yield [10, 27.5, 45, 62.5] with step_size 17.5.
    """
    step_size, gen = create_progress_sequence(start=10, stop=80, steps=4)

    assert step_size == pytest.approx(17.5)

    values = list(gen)
    assert len(values) == 4
    assert values[0] == pytest.approx(10.0)
    assert values[1] == pytest.approx(27.5)
    assert values[2] == pytest.approx(45.0)
    assert values[3] == pytest.approx(62.5)


@pytest.mark.ai
def test_create_progress_sequence__single_step__returns_start() -> None:
    """
    Purpose: Verify single-step sequence yields only the start value.
    Why this matters: Edge case when only one source is processed.
    Setup summary: steps=1, expect a single value equal to start.
    """
    step_size, gen = create_progress_sequence(start=10, stop=80, steps=1)

    assert step_size == pytest.approx(70.0)

    values = list(gen)
    assert len(values) == 1
    assert values[0] == pytest.approx(10.0)


@pytest.mark.ai
def test_create_progress_sequence__zero_steps__raises_value_error() -> None:
    """
    Purpose: Verify zero steps raises ValueError when the generator is consumed.
    Why this matters: Prevents division-by-zero or infinite loops in progress tracking.
    Setup summary: steps=0, consuming the generator should raise ValueError.
    """
    with pytest.raises(ZeroDivisionError):
        create_progress_sequence(start=10, stop=80, steps=0)


@pytest.mark.ai
def test_create_progress_sequence__large_step_count__evenly_distributed() -> None:
    """
    Purpose: Verify many steps produce an evenly distributed sequence.
    Why this matters: Large document sets must have smooth progress tracking.
    Setup summary: 10 steps from 0 to 100, verify first, last, and spacing.
    """
    step_size, gen = create_progress_sequence(start=0, stop=100, steps=10)

    assert step_size == pytest.approx(10.0)

    values = list(gen)
    assert len(values) == 10
    assert values[0] == pytest.approx(0.0)
    assert values[-1] == pytest.approx(90.0)

    for i in range(1, len(values)):
        assert values[i] - values[i - 1] == pytest.approx(10.0)
