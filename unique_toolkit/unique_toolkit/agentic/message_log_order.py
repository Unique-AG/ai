"""Per-request message log order counters (public API).

``MessageStepLogger`` and :meth:`~unique_toolkit.services.chat_service.ChatService.complete_responses_with_references_async`
share the same sequence so user-visible steps and rate-limit banners interleave with
correct ``order`` values.

This module lives outside the ``message_log_manager`` package intentionally: importing
``message_log_manager`` triggers its ``__init__.py`` which pulls in ``ChatService``,
creating a circular import. Placing this module one level up breaks the cycle while
keeping the counters accessible to both callers.
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
