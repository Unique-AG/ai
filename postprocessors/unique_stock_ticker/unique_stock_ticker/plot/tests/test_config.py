from datetime import date, timedelta

from unique_stock_ticker.plot.config import OffSetDate, StockTickerDataRetrievalConfig


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
    Why this matters: Edge case - today should be valid.
    Setup summary: Provide today's date and assert it is accepted.
    """
    # Arrange
    today = date.today()

    # Act
    config = StockTickerDataRetrievalConfig(start_date=today)

    # Assert
    assert config.start_date == today


def test_start_date__accepts_offset_date__negative_offset() -> None:
    """
    Purpose: Verify that start_date accepts an OffSetDate with negative offset.
    Why this matters: Allows users to specify relative dates for convenience.
    Setup summary: Provide an OffSetDate with negative offset and assert it is accepted.
    """
    # Arrange
    offset_date = OffSetDate(anchor="today", offset=timedelta(days=-30))

    # Act
    config = StockTickerDataRetrievalConfig(start_date=offset_date)

    # Assert
    assert config.start_date == offset_date


def test_start_date__accepts_offset_date__zero_offset() -> None:
    """
    Purpose: Verify that start_date accepts an OffSetDate with zero offset.
    Why this matters: Edge case where offset of 0 should equal today.
    Setup summary: Provide an OffSetDate with zero offset and assert it is accepted.
    """
    # Arrange
    offset_date = OffSetDate(anchor="today", offset=timedelta(days=0))

    # Act
    config = StockTickerDataRetrievalConfig(start_date=offset_date)

    # Assert
    assert config.start_date == offset_date


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


def test_effective_start_date__returns_date__when_start_date_is_date() -> None:
    """
    Purpose: Verify that effective_start_date returns the date when start_date is a date.
    Why this matters: Property should pass through plain dates unchanged.
    Setup summary: Provide a date and assert effective_start_date equals start_date.
    """
    # Arrange
    past_date = date.today() - timedelta(days=30)

    # Act
    config = StockTickerDataRetrievalConfig(start_date=past_date)

    # Assert
    assert config.effective_start_date == past_date


def test_effective_start_date__resolves_offset_date__negative_offset() -> None:
    """
    Purpose: Verify that effective_start_date resolves OffSetDate to a concrete date.
    Why this matters: Property should compute the actual date from OffSetDate.
    Setup summary: Provide an OffSetDate and assert effective_start_date equals the computed date.
    """
    # Arrange
    offset = timedelta(days=-30)
    offset_date = OffSetDate(anchor="today", offset=offset)
    expected_date = date.today() + offset

    # Act
    config = StockTickerDataRetrievalConfig(start_date=offset_date)

    # Assert
    assert config.effective_start_date == expected_date


def test_effective_start_date__resolves_offset_date__zero_offset() -> None:
    """
    Purpose: Verify that effective_start_date resolves OffSetDate with zero offset to today.
    Why this matters: Edge case where zero offset should resolve to today's date.
    Setup summary: Provide an OffSetDate with zero offset and assert effective_start_date equals today.
    """
    # Arrange
    offset_date = OffSetDate(anchor="today", offset=timedelta(days=0))

    # Act
    config = StockTickerDataRetrievalConfig(start_date=offset_date)

    # Assert
    assert config.effective_start_date == date.today()


def test_offset_date__computes_date__from_today_with_offset() -> None:
    """
    Purpose: Verify that OffSetDate.date computes the correct date.
    Why this matters: Core functionality of the OffSetDate model.
    Setup summary: Create OffSetDate and assert date property equals today + offset.
    """
    # Arrange
    offset = timedelta(days=-15)
    offset_date = OffSetDate(anchor="today", offset=offset)

    # Act & Assert
    assert offset_date.date == date.today() + offset


def test_offset_date__uses_default_offset__when_not_provided() -> None:
    """
    Purpose: Verify that OffSetDate defaults offset to zero.
    Why this matters: Ensures sensible default behavior.
    Setup summary: Create OffSetDate without offset and assert date equals today.
    """
    # Arrange & Act
    offset_date = OffSetDate(anchor="today")

    # Assert
    assert offset_date.offset == timedelta(days=0)
    assert offset_date.date == date.today()
