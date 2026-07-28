"""Request-scoped tenant context for logging and diagnostics."""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import Final

from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext

_REQUEST_CONTEXT: ContextVar[RequestContext] = ContextVar(
    "request_context",
    default=LOCAL_REQUEST_CONTEXT,
)

_CONTEXT_FIELDS: Final[tuple[str, ...]] = ("company_id", "user_id", "chat_id")


def bind_request_context(context: RequestContext) -> Token[RequestContext]:
    """Bind tenant context for the current async task."""
    return _REQUEST_CONTEXT.set(context)


def reset_request_context(token: Token[RequestContext]) -> None:
    """Restore the previous tenant context."""
    _REQUEST_CONTEXT.reset(token)


def get_request_context() -> RequestContext:
    """Return the tenant context for the current async task."""
    return _REQUEST_CONTEXT.get()


class RequestContextLogFilter(logging.Filter):
    """Inject tenant context fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = get_request_context()
        for field_name in _CONTEXT_FIELDS:
            setattr(record, field_name, getattr(context, field_name))
        return True


__all__ = [
    "RequestContextLogFilter",
    "bind_request_context",
    "get_request_context",
    "reset_request_context",
]
