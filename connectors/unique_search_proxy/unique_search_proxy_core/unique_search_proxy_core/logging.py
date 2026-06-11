"""Shared logging helpers for proxy server and SDK."""

from __future__ import annotations

import logging

_HTTPS_REQUEST_LOG_PREFIX = "HTTP Request:"


class HttpxRequestLogFilter(logging.Filter):
    """Drop httpx per-request access logs.

    httpx logs full request URLs at INFO, which can include query parameters,
    search terms, and provider credentials (e.g. Google ``key=``).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "httpx":
            return True
        return not record.getMessage().startswith(_HTTPS_REQUEST_LOG_PREFIX)


def suppress_httpx_request_logs() -> None:
    """Attach :class:`HttpxRequestLogFilter` to the ``httpx`` logger (idempotent)."""
    httpx_logger = logging.getLogger("httpx")
    if any(isinstance(f, HttpxRequestLogFilter) for f in httpx_logger.filters):
        return
    httpx_logger.addFilter(HttpxRequestLogFilter())


__all__ = ["HttpxRequestLogFilter", "suppress_httpx_request_logs"]
