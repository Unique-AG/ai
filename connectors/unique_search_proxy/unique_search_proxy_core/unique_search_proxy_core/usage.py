"""Per-request usage record emitted as a structured log line."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from unique_search_proxy_core.context import EntryPoint

_LOGGER = logging.getLogger(__name__)


class UsageRecord(BaseModel):
    """Who triggered a billable provider operation. Never holds queries or URLs."""

    event: Literal["web_search_usage"] = "web_search_usage"
    # Take the trace id from unique_toolkit.monitoring.tracing once the proxy adopts tracing.
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    company_id: str
    user_id: str
    chat_id: str
    entry_point: EntryPoint
    caller: str
    endpoint: Literal["search", "agent_search", "crawl"]
    provider: str
    units: int
    status: Literal["success", "error"]
    duration_ms: int


def record_usage(record: UsageRecord) -> None:
    """Write ``record`` as one JSON log line."""
    _LOGGER.info(record.model_dump_json())


__all__ = ["UsageRecord", "record_usage"]
