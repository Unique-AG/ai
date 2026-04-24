"""``unique_toolkit.experimental.resources.scheduled_task`` — cron-based assistant triggers.

.. warning::

    **Experimental.** This subpackage is exposed under
    :mod:`unique_toolkit.experimental` and its public API may change without
    notice. It is not covered by the toolkit's normal stability guarantees.

A thin, typed wrapper around :class:`unique_sdk.ScheduledTask`. The single
entry point is :class:`ScheduledTasks`; the subpackage also re-exports the
Pydantic schemas used on responses, plus a :class:`Cron` ``StrEnum`` of
ready-made cron strings for the most common schedules.

**Classification note (reorg proposal).** This subpackage stays under
:mod:`..resources` even though it ships its own :mod:`.cron` helper: the
``Cron`` enum is single-purpose plumbing for the resource (the backend
expects cron strings on every mutation), it imports nothing outside this
package, and extracting it would only split one cohesive SDK wrapper into
two without improving the public surface. Promote ``cron`` to
:mod:`..components` only if a second resource starts needing it.
"""

from unique_toolkit.experimental.resources.scheduled_task.cron import Cron as Cron
from unique_toolkit.experimental.resources.scheduled_task.functions import (
    DeletedScheduledTask,
    ScheduledTask,
    create_scheduled_task,
    create_scheduled_task_async,
    delete_scheduled_task,
    delete_scheduled_task_async,
    get_scheduled_task,
    get_scheduled_task_async,
    list_scheduled_tasks,
    list_scheduled_tasks_async,
    update_scheduled_task,
    update_scheduled_task_async,
)
from unique_toolkit.experimental.resources.scheduled_task.service import ScheduledTasks

__all__ = [
    "Cron",
    "DeletedScheduledTask",
    "ScheduledTask",
    "ScheduledTasks",
    "create_scheduled_task",
    "create_scheduled_task_async",
    "delete_scheduled_task",
    "delete_scheduled_task_async",
    "get_scheduled_task",
    "get_scheduled_task_async",
    "list_scheduled_tasks",
    "list_scheduled_tasks_async",
    "update_scheduled_task",
    "update_scheduled_task_async",
]
