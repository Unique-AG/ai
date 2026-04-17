"""``unique_toolkit.experimental.scheduled_task`` — cron-based assistant triggers.

.. warning::

    **Experimental.** This subpackage is exposed under
    :mod:`unique_toolkit.experimental` and its public API may change without
    notice. It is not covered by the toolkit's normal stability guarantees.

A thin, typed wrapper around :class:`unique_sdk.ScheduledTask`. The single
entry point is :class:`ScheduledTasks`; the subpackage also re-exports the
Pydantic schemas used on responses, plus a :class:`Cron` ``StrEnum`` of
ready-made cron strings for the most common schedules.
"""

from unique_toolkit.experimental.scheduled_task.cron import Cron as Cron
from unique_toolkit.experimental.scheduled_task.functions import (
    create_scheduled_task as create_scheduled_task,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    create_scheduled_task_async as create_scheduled_task_async,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    delete_scheduled_task as delete_scheduled_task,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    delete_scheduled_task_async as delete_scheduled_task_async,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    get_scheduled_task as get_scheduled_task,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    get_scheduled_task_async as get_scheduled_task_async,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    list_scheduled_tasks as list_scheduled_tasks,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    list_scheduled_tasks_async as list_scheduled_tasks_async,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    update_scheduled_task as update_scheduled_task,
)
from unique_toolkit.experimental.scheduled_task.functions import (
    update_scheduled_task_async as update_scheduled_task_async,
)
from unique_toolkit.experimental.scheduled_task.schemas import (
    DeletedScheduledTask as DeletedScheduledTask,
)
from unique_toolkit.experimental.scheduled_task.schemas import (
    ScheduledTask as ScheduledTask,
)
from unique_toolkit.experimental.scheduled_task.service import (
    ScheduledTasks as ScheduledTasks,
)

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
