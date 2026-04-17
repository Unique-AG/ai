"""``unique_toolkit.experimental`` — opt-in surface for experimental services.

.. warning::

    Anything exported from this subpackage is **experimental**. The public API,
    method names, argument shapes, and return types may change at any time and
    are **not** covered by the toolkit's normal stability guarantees. Pin the
    toolkit version if you depend on a specific shape.

Currently exposes:

- :class:`unique_toolkit.experimental.scheduled_task.ScheduledTasks` — cron-based
  scheduled tasks that trigger assistants on a recurring schedule (wrapper over
  :class:`unique_sdk.ScheduledTask`).
- :class:`unique_toolkit.experimental.identity.Identity` — users + groups
  management (Linux-inspired wrapper over :mod:`unique_sdk.User` and
  :mod:`unique_sdk.Group`).
"""

from unique_toolkit.experimental.identity import Identity as Identity
from unique_toolkit.experimental.scheduled_task import (
    ScheduledTasks as ScheduledTasks,
)

__all__ = [
    "Identity",
    "ScheduledTasks",
]
