from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from unique_stock_ticker.plot.backend.base.schema import (
    MetricName,
    PriceHistoryItem,
    StockHistoryPlotPayload,
    StockInfo,
    StockMetric,
)
from unique_stock_ticker.plot.backend.html import (
    HtmlPlottingBackend,
    HtmlTickerPlotConfig,
    render_stock_dashboard_html,
)


def _build_payload() -> StockHistoryPlotPayload:
    return StockHistoryPlotPayload(
        info=StockInfo(
            company_name="Apple Inc",
            instrument_name="Apple Rg",
            ticker="AAPL",
            exchange="NASDAQ",
            currency="USD",
        ),
        price_history=[
            PriceHistoryItem(date=date(2026, 4, 7), value=255.12),
            PriceHistoryItem(date=date(2026, 4, 8), value=256.24),
            PriceHistoryItem(date=date(2026, 4, 9), value=257.50),
        ],
        metrics=[
            StockMetric(
                name=MetricName.OPEN,
                value=258.2,
                timestamp=datetime(2026, 4, 9, 8, 30, tzinfo=UTC),
            ),
            StockMetric(
                name=MetricName.MARKET_CAP,
                value=3_800_000_000_000,
                timestamp=datetime(2026, 4, 9, 8, 30, tzinfo=UTC),
            ),
            StockMetric(
                name=MetricName.DIVIDEND_YIELD,
                value=0.402,
                timestamp=datetime(2026, 4, 9, 8, 30, tzinfo=UTC),
            ),
        ],
        last_updated=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
    )


def test_render_stock_dashboard_html__embeds_payload__with_real_ticker_data() -> None:
    """
    Purpose: Verify that the HTML template is filled with the serialized ticker payload.
    Why this matters: The frontend dashboard can only render the stock view if the uploaded HTML contains the API data instead of demo placeholders.
    Setup summary: Render a representative payload and assert the output contains the ticker metadata, metrics, and Plotly bootstrap data.
    """
    # Arrange
    payload = _build_payload()

    # Act
    html = render_stock_dashboard_html(payload)

    # Assert
    assert "const dashboardData =" in html
    assert '"ticker": "AAPL"' in html
    assert '"companyName": "Apple Inc"' in html
    assert '"Market Cap"' in html
    assert '"value": 257.5' in html


def test_html_plotting_backend__uploads_html_and_returns_rendering_block() -> None:
    """
    Purpose: Verify that the HTML backend uploads a generated dashboard and returns an HtmlRendering block.
    Why this matters: The stock postprocessor needs the same fetchable HTML artifact flow as code execution for the dashboard to render in chat.
    Setup summary: Mock chat uploads, plot a sample payload, and assert both the uploaded file metadata and returned rendering block are correct.
    """
    # Arrange
    backend = HtmlPlottingBackend(
        config=HtmlTickerPlotConfig(render_width=840, render_height=620),
        company_id="company-123",
        user_id="user-123",
        chat_id="chat-123",
    )

    # Act
    with patch(
        "unique_stock_ticker.plot.backend.html.upload_content_from_bytes",
        return_value=SimpleNamespace(id="content-123"),
    ) as upload_content:
        rendering_block = backend.plot([_build_payload()])

    # Assert
    upload_content.assert_called_once()
    _, kwargs = upload_content.call_args
    assert kwargs["user_id"] == "user-123"
    assert kwargs["company_id"] == "company-123"
    assert kwargs["chat_id"] == "chat-123"
    assert kwargs["content_name"] == "stock_dashboard_aapl.html"
    assert kwargs["mime_type"] == "text/html"
    assert kwargs["skip_ingestion"] is True
    assert kwargs["hide_in_chat"] is True
    assert b'"ticker": "AAPL"' in kwargs["content"]
    assert rendering_block == (
        "```HtmlRendering\n840px\n620px\n\nunique://content/content-123\n\n```"
    )
