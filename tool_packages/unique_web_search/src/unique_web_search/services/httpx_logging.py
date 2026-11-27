"""Hide httpx request logs while a web search call runs.

httpx logs every request URL at INFO, and web search request URLs carry
search queries, crawled URLs and provider credentials. httpx logs from other
code in the same process are kept.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from unique_search_proxy_core.logging import HttpxRequestLogFilter

_hide_httpx_request_logs: ContextVar[bool] = ContextVar(
    "unique_web_search_hide_httpx_request_logs", default=False
)


# Wraps instead of subclassing HttpxRequestLogFilter: the SDK's global
# suppress_httpx_request_logs() skips installing itself when it finds an
# instance of that class on the httpx logger.
class _WebSearchHttpxRequestLogFilter(logging.Filter):
    _request_log_filter = HttpxRequestLogFilter()

    def filter(self, record: logging.LogRecord) -> bool:
        if not _hide_httpx_request_logs.get():
            return True
        return self._request_log_filter.filter(record)


def _install_filter() -> None:
    httpx_logger = logging.getLogger("httpx")
    if any(
        isinstance(log_filter, _WebSearchHttpxRequestLogFilter)
        for log_filter in httpx_logger.filters
    ):
        return
    httpx_logger.addFilter(_WebSearchHttpxRequestLogFilter())


@contextmanager
def hide_httpx_request_logs() -> Iterator[None]:
    """Drop httpx request logs from the current task and tasks it starts.

    Scoping follows ``contextvars``: work handed to threads without a copied
    context (e.g. ``loop.run_in_executor``) is not covered.
    """
    _install_filter()
    token = _hide_httpx_request_logs.set(True)
    try:
        yield
    finally:
        _hide_httpx_request_logs.reset(token)
