from __future__ import annotations

import logging
from typing import Any

import pytest

from unique_toolkit.experimental.resources.activity_records.publishers.logging_publisher import (
    LoggingPublisher,
)

EVENT: Any = {
    "id": "e1",
    "type": "t",
    "data": {"criticalData": {"userPrompt": "secret"}},
}


@pytest.mark.ai
@pytest.mark.asyncio
async def test_publish__by_default__logs_id_and_type_but_not_the_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        await LoggingPublisher().publish([EVENT])

    assert "id=e1 type=t" in caplog.text
    assert "secret" not in caplog.text


@pytest.mark.ai
@pytest.mark.asyncio
async def test_publish__with_include_payload__logs_the_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        await LoggingPublisher(include_payload=True).publish([EVENT])

    assert "secret" in caplog.text
