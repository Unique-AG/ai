"""A sender that only logs, for testing the outbox end to end."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from unique_toolkit.experimental.resources.activity_records.json_size import json_bytes
from unique_toolkit.experimental.resources.activity_records.prepare import WireEvent

logger = logging.getLogger(__name__)


class LoggingPublisher:
    """Local testing sender: logs each event and reports success without delivering it, so
    the outbox rows are deleted. Logs client data by default. Never use it in production."""

    def __init__(self, *, include_payload: bool = True) -> None:
        self.include_payload = include_payload

    async def publish(self, events: Sequence[WireEvent]) -> None:
        logger.info("Activity events batch: count=%d", len(events))
        for event in events:
            if self.include_payload:
                logger.info("Activity event: %s", json_bytes(event).decode("utf-8"))
            else:
                logger.info(
                    "Activity event: id=%s type=%s", event.get("id"), event.get("type")
                )
