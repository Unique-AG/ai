"""Pydantic schemas for the :mod:`unique_toolkit.experimental.resources.scheduled_task` subpackage.

These models mirror the :class:`unique_sdk.ScheduledTask` TypedDicts but add:

- field-level documentation (``Field(..., description=...)``) so the intent of each
  attribute is visible in IDEs, the docs site, and ``help(...)``;
- camelCase aliases so the SDK's wire payload (``cronExpression``, ``assistantId``, …)
  can be validated directly via :meth:`BaseModel.model_validate`.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`; the public
    shape of these models may still change without notice.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

_model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


class ScheduledTask(BaseModel):
    """A cron-based scheduled task that triggers an assistant on a recurring schedule.

    Scheduled tasks are stored and executed on the Unique AI Platform by a
    Kubernetes CronJob — they are **not** local crontab entries. Every minute,
    the platform evaluates all enabled tasks and triggers the ones whose cron
    expression matches the current time (UTC).

    Each task carries:

    - a :attr:`cron_expression` in **5-field UTC** form,
    - the :attr:`assistant_id` to execute on each tick,
    - the :attr:`prompt` sent to that assistant,
    - an optional :attr:`chat_id` used to *continue* an existing conversation
      (omit / set to ``None`` to get a fresh chat on every run), and
    - an :attr:`enabled` flag to pause/resume execution without deleting the task.

    Maps to ``unique_sdk.ScheduledTask`` and is the return value of every toolkit
    CRUD method except :meth:`~unique_toolkit.experimental.resources.scheduled_task.service.ScheduledTasks.delete`.
    """

    model_config = _model_config

    id: str = Field(
        description=(
            "Unique scheduled-task identifier. Stable for the lifetime of the "
            "task; use it to :meth:`get`, :meth:`update`, or :meth:`delete` "
            "later."
        ),
    )
    object: Literal["scheduled_task"] = Field(
        default="scheduled_task",
        description=(
            'Server-side object-type tag; always the literal ``"scheduled_task"``.'
        ),
    )
    cron_expression: str = Field(
        description=(
            "5-field cron expression evaluated in **UTC** as returned by the "
            "server. Stored as the raw wire string so that compound patterns "
            "(ranges, steps, lists) survive round-trips; use "
            ":meth:`CronExpression.parse` on the client if you want a typed "
            "view."
        ),
    )

    assistant_id: str = Field(
        description=(
            "Id of the assistant to invoke on each trigger. Typically starts with "
            "``assistant_``. The acting user must have access to the assistant."
        ),
    )
    assistant_name: str | None = Field(
        default=None,
        description=(
            "Display name of the assistant, as resolved by the server at read time. "
            "``None`` if the assistant was deleted or the caller cannot see it."
        ),
    )
    chat_id: str | None = Field(
        default=None,
        description=(
            "Id of the chat to continue on each trigger. When ``None`` (the default), "
            "a brand-new chat is created for every run; when set, the assistant "
            "appends to that chat, so prompts should be idempotent or progressive."
        ),
    )
    prompt: str = Field(
        description=(
            "Prompt text delivered to the assistant on every trigger. Treat as a "
            "user message sent by the acting user."
        ),
    )
    enabled: bool = Field(
        description=(
            "Whether the task is active. Disabled tasks are preserved (id, cron, "
            "history) but are skipped by the scheduler until re-enabled."
        ),
    )
    last_run_at: datetime | None = Field(
        default=None,
        description=(
            "ISO-8601 timestamp of the last execution, or ``None`` if the task has "
            "never run (e.g. freshly created or permanently disabled)."
        ),
    )
    created_at: datetime = Field(
        description="ISO-8601 timestamp set by the server when the task was created.",
    )
    updated_at: datetime = Field(
        description=(
            "ISO-8601 timestamp of the last modification, including toggles of "
            ":attr:`enabled` and edits to :attr:`chat_id` or :attr:`prompt`."
        ),
    )


class DeletedScheduledTask(BaseModel):
    """Response returned by :meth:`unique_sdk.ScheduledTask.delete`.

    The API echoes the deleted task's id and flags the row as removed. Deletion
    is permanent; a deleted task cannot be recovered, so re-scheduling requires
    calling :meth:`~unique_toolkit.experimental.resources.scheduled_task.service.ScheduledTasks.create`
    with fresh parameters.
    """

    model_config = _model_config

    id: str = Field(description="Id of the scheduled task that was deleted.")
    object: Literal["scheduled_task"] = Field(
        default="scheduled_task",
        description=(
            'Server-side object-type tag; always the literal ``"scheduled_task"``.'
        ),
    )
    deleted: bool = Field(
        description=(
            "``True`` when the server successfully removed the row. The toolkit "
            "surfaces this verbatim — a ``False`` value should be treated as an "
            "unexpected server response and reported."
        ),
    )
