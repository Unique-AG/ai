from unique_stock_ticker.detection.prompt import (
    SYSTEM_MESSAGE_STOCK_TICKER_QUERY,
    USER_MESSAGE_STOCK_TICKER_QUERY,
)


def test_system_message_stock_ticker_query():
    # Check that the system message contains certain key phrases
    assert (
        "Below are a message from a user and a message from the assistant."
        in SYSTEM_MESSAGE_STOCK_TICKER_QUERY
    )


def test_user_message_stock_ticker_query():
    # Check that user message prompt is correctly formatted with placeholders
    assert "${user_message}" in USER_MESSAGE_STOCK_TICKER_QUERY
    assert "${assistant_message}" in USER_MESSAGE_STOCK_TICKER_QUERY
    assert "Identify the stock symbols" in USER_MESSAGE_STOCK_TICKER_QUERY
    assert "Response:" in USER_MESSAGE_STOCK_TICKER_QUERY
