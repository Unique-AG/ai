from unittest.mock import MagicMock

import pytest

from unique_stock_ticker.plot.backend.plotly.save import (
    _save_plot_to_content_service,
)


@pytest.mark.ai
def test_save_plot_to_content_service__omits_assistant_generated__scope_upload() -> (
    None
):
    """
    Purpose: Verify a scope plot upload does not set assistantGenerated metadata.
    Why this matters: The flag is only read on chat-owned content. A scope row
        stays under knowledge-base permissions, so marking it does not let a
        shared-chat recipient open the chart.
    Setup summary: Upload a stub figure into a scope and assert the upload
        carries no metadata.
    """
    # Arrange
    fig = MagicMock()
    fig.to_image.return_value = b"jpeg-bytes"
    content_service = MagicMock()
    content_service.upload_content_from_bytes.return_value.id = "content-1"

    # Act
    content_id = _save_plot_to_content_service(
        fig=fig,
        content_service=content_service,
        scope_id="scope-1",
        filename="chart.jpeg",
    )

    # Assert
    assert content_id == "content-1"
    upload_kwargs = content_service.upload_content_from_bytes.call_args.kwargs
    assert upload_kwargs["scope_id"] == "scope-1"
    assert "metadata" not in upload_kwargs
