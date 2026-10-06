from __future__ import annotations

import time
from typing import Literal

from unique_search_proxy_core.usage import UsageRecord, record_usage

from unique_search_proxy_client.web.context import get_request_context
from unique_search_proxy_client.web.monitoring.metrics import record_request


def record_request_usage(
    endpoint: Literal["search", "agent_search", "crawl"],
    provider: str,
    *,
    units: int,
    succeeded: bool,
    started: float,
) -> None:
    """Emit the usage log line and counter for the current request."""
    context = get_request_context()
    status = "success" if succeeded else "error"
    record_usage(
        UsageRecord(
            company_id=context.company_id,
            user_id=context.user_id,
            chat_id=context.chat_id,
            entry_point=context.entry_point,
            caller=context.caller,
            endpoint=endpoint,
            provider=provider,
            units=units,
            status=status,
            duration_ms=round((time.perf_counter() - started) * 1000),
        ),
    )
    record_request(context, endpoint, provider, status)
