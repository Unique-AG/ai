"""Per-request message log order counters (public API).

``MessageStepLogger`` and :meth:`~unique_toolkit.services.chat_service.ChatService.complete_responses_with_references_async`
share the same sequence so user-visible steps and rate-limit banners interleave with
correct ``order`` values.

This module does not import ``ChatService`` or ``chat.service``, so
``unique_toolkit.services.chat_service`` can import :func:`next_message_log_order` at
module load time without circular imports.
"""

from collections import defaultdict

_counters: defaultdict[str, int] = defaultdict(int)


def next_message_log_order(*, message_id: str) -> int:
    """Increment and return the next order index for logs belonging to ``message_id``."""
    _counters[message_id] += 1
    return _counters[message_id]


def reset_message_log_order_counters() -> None:
    """Clear all order counters (intended for test fixtures)."""
    _counters.clear()
