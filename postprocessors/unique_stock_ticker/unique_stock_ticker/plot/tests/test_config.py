from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from unique_stock_ticker.plot.config import StockTickerDataRetrievalConfig


def test_start_date__accepts_date__valid_past_date() -> None:
    """
    Purpose: Verify that start_date accepts a valid date in the past.
    Why this matters: Core functionality for configuring data retrieval.
    Setup summary: Provide a past date and assert it is accepted.
    """
    # Arrange
    past_date = date.today() - timedelta(days=30)

    # Act
    config = StockTickerDataRetrievalConfig(start_date=past_date)

    # Assert
    assert config.start_date == past_date


def test_start_date__accepts_date__today() -> None:
    """
    Purpose: Verify that start_date accepts today's date.
    Why this matters: Edge case - today should be valid as it's not in the future.
    Setup summary: Provide today's date and assert it is accepted.
    """
    # Arrange
    today = date.today()

    # Act
    config = StockTickerDataRetrievalConfig(start_date=today)

    # Assert
    assert config.start_date == today


def test_start_date__converts_timedelta__negative_days() -> None:
    """
    Purpose: Verify that a negative timedelta is converted to a past date.
    Why this matters: Allows users to specify relative dates for convenience.
    Setup summary: Provide a negative timedelta and assert it converts to the correct date.
    """
    # Arrange
    delta = timedelta(days=-30)
    expected_date = date.today() + delta

    # Act
    config = StockTickerDataRetrievalConfig(start_date=delta)

    # Assert
    assert config.start_date == expected_date


def test_start_date__converts_timedelta__zero_days() -> None:
    """
    Purpose: Verify that a zero timedelta results in today's date.
    Why this matters: Edge case where timedelta(0) should equal today.
    Setup summary: Provide a zero timedelta and assert it equals today.
    """
    # Arrange
    delta = timedelta(days=0)

    # Act
    config = StockTickerDataRetrievalConfig(start_date=delta)

    # Assert
    assert config.start_date == date.today()


def test_start_date__raises_error__future_date() -> None:
    """
    Purpose: Verify that a future date raises a ValidationError.
    Why this matters: Prevents invalid configurations that can't retrieve future data.
    Setup summary: Provide a future date and assert ValidationError is raised.
    """
    # Arrange
    future_date = date.today() + timedelta(days=1)

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        StockTickerDataRetrievalConfig(start_date=future_date)

    assert "Start date must be in the past" in str(exc_info.value)


def test_start_date__raises_error__positive_timedelta() -> None:
    """
    Purpose: Verify that a positive timedelta (future) raises a ValidationError.
    Why this matters: Timedelta conversion should still enforce the past date constraint.
    Setup summary: Provide a positive timedelta and assert ValidationError is raised.
    """
    # Arrange
    delta = timedelta(days=1)

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        StockTickerDataRetrievalConfig(start_date=delta)

    assert "Start date must be in the past" in str(exc_info.value)


def test_start_date__uses_default__when_not_provided() -> None:
    """
    Purpose: Verify that start_date defaults to the start of the current year.
    Why this matters: Ensures sensible default behavior.
    Setup summary: Create config without start_date and assert default value.
    """
    # Arrange
    expected_default = date(date.today().year, 1, 1)

    # Act
    config = StockTickerDataRetrievalConfig()

    # Assert
    assert config.start_date == expected_default
