"""The :class:`ScheduledTasks` service — manage cron-based assistant triggers.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The
    public API, method names, and return shapes may change without notice
    and are not covered by the toolkit's normal stability guarantees.

Wraps :class:`unique_sdk.ScheduledTask` with a thin, typed service:

- :meth:`ScheduledTasks.create_task` — register a new cron schedule.
- :meth:`ScheduledTasks.list_tasks` — enumerate all tasks visible to the user.
- :meth:`ScheduledTasks.get_task` — single-task lookup by id.
- :meth:`ScheduledTasks.update_task` — server-side partial update; supports
  explicit ``clear_chat_id=True`` for the "new chat each run" intent.
- :meth:`ScheduledTasks.delete_task` — permanent removal.

Every sync method has a matching ``*_async`` sibling with the same signature.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.scheduled_task.functions import (
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
from unique_toolkit.experimental.scheduled_task.schemas import (
    DeletedScheduledTask,
    ScheduledTask,
)

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueContext


class ScheduledTasks:
    """Service for managing cron-based scheduled tasks on the Unique AI Platform.

    .. warning::

        **Experimental.** Import path is
        :mod:`unique_toolkit.experimental.scheduled_task`. The API may change
        without notice.

    **What is a scheduled task?** A task stored on the platform that, on every
    cron tick, triggers an assistant with a prompt. Tasks are executed by a
    Kubernetes CronJob (not a local crontab). All cron expressions are
    evaluated in **UTC** — convert local times before assigning them.

    **Chat continuity.** When :attr:`ScheduledTask.chat_id` is ``None``, each
    run creates a fresh chat (the common case for idempotent reports). When
    set, the assistant appends to that chat on every run — prefer prompts that
    are additive or progressive. Use :meth:`update_task` with
    ``clear_chat_id=True`` to drop the link and revert to "fresh chat each run".

    **Enabled flag.** :attr:`ScheduledTask.enabled` pauses the task without
    deleting it. The task metadata (cron, prompt, assistant) is preserved and
    resumes on the next matching tick after you flip it back on.

    **Acting user.** Every API call is made on behalf of the user bound to the
    service (``self._user_id``), which must have access to the referenced
    assistant and, if applicable, the referenced chat.
    """

    def __init__(
        self,
        company_id: str,
        user_id: str,
    ) -> None:
        [company_id, user_id] = validate_required_values([company_id, user_id])
        self._company_id = company_id
        self._user_id = user_id

    # ── Construction ──────────────────────────────────────────────────────

    @classmethod
    def from_context(cls, context: UniqueContext) -> Self:
        """Create from a :class:`UniqueContext` (preferred constructor)."""
        return cls(
            company_id=context.auth.get_confidential_company_id(),
            user_id=context.auth.get_confidential_user_id(),
        )

    @classmethod
    def from_settings(
        cls,
        settings: UniqueSettings,
    ) -> Self:
        """Create from :class:`UniqueSettings` (used by :class:`UniqueServiceFactory`)."""
        return cls.from_context(
            context=settings.context,
        )

    # ── Create ────────────────────────────────────────────────────────────

    def create_task(
        self,
        *,
        cron_expression: str,
        assistant_id: str,
        prompt: str,
        enabled: bool = True,
        chat_id: str | None = None,
    ) -> ScheduledTask:
        """Register a new scheduled task.

        Args:
            cron_expression: 5-field UTC cron expression
                (``"minute hour day-of-month month day-of-week"``).
            assistant_id: Assistant to execute on every trigger.
            prompt: Prompt delivered to the assistant on each run.
            enabled: Whether the task is active from creation. Defaults to
                ``True`` so tasks fire immediately; pass ``False`` to stage a
                task that can be enabled later via :meth:`enable_task`.
            chat_id: Optional chat to continue. ``None`` (default) means a
                fresh chat on every run.

        Returns:
            The created :class:`ScheduledTask` as echoed by the server.
        """
        return create_scheduled_task(
            user_id=self._user_id,
            company_id=self._company_id,
            cron_expression=cron_expression,
            assistant_id=assistant_id,
            prompt=prompt,
            chat_id=chat_id,
            enabled=enabled,
        )

    async def create_task_async(
        self,
        *,
        cron_expression: str,
        assistant_id: str,
        prompt: str,
        enabled: bool = True,
        chat_id: str | None = None,
    ) -> ScheduledTask:
        """Async :meth:`create_task`."""
        return await create_scheduled_task_async(
            user_id=self._user_id,
            company_id=self._company_id,
            cron_expression=cron_expression,
            assistant_id=assistant_id,
            prompt=prompt,
            chat_id=chat_id,
            enabled=enabled,
        )

    # ── List / get ────────────────────────────────────────────────────────

    def list_tasks(self) -> list[ScheduledTask]:
        """Return every scheduled task visible to the acting user."""
        return list_scheduled_tasks(
            user_id=self._user_id,
            company_id=self._company_id,
        )

    async def list_tasks_async(self) -> list[ScheduledTask]:
        """Async :meth:`list_tasks`."""
        return await list_scheduled_tasks_async(
            user_id=self._user_id,
            company_id=self._company_id,
        )

    def get_task(self, *, task_id: str) -> ScheduledTask:
        """Fetch a single scheduled task by id."""
        return get_scheduled_task(
            user_id=self._user_id,
            company_id=self._company_id,
            task_id=task_id,
        )

    async def get_task_async(self, *, task_id: str) -> ScheduledTask:
        """Async :meth:`get_task`."""
        return await get_scheduled_task_async(
            user_id=self._user_id,
            company_id=self._company_id,
            task_id=task_id,
        )

    # ── Update ────────────────────────────────────────────────────────────

    def update_task(
        self,
        *,
        task_id: str,
        cron_expression: str | None = None,
        assistant_id: str | None = None,
        prompt: str | None = None,
        chat_id: str | None = None,
        clear_chat_id: bool = False,
        enabled: bool | None = None,
    ) -> ScheduledTask:
        """Server-side partial update of an existing scheduled task.

        Only the fields you pass are changed. To drop the current chat link so
        that every future run spawns a fresh chat, pass ``clear_chat_id=True``
        — this is mutually exclusive with ``chat_id=`` and mixing them raises
        :class:`TypeError`.
        """
        return update_scheduled_task(
            user_id=self._user_id,
            company_id=self._company_id,
            task_id=task_id,
            cron_expression=cron_expression,
            assistant_id=assistant_id,
            prompt=prompt,
            chat_id=chat_id,
            clear_chat_id=clear_chat_id,
            enabled=enabled,
        )

    async def update_task_async(
        self,
        *,
        task_id: str,
        cron_expression: str | None = None,
        assistant_id: str | None = None,
        prompt: str | None = None,
        chat_id: str | None = None,
        clear_chat_id: bool = False,
        enabled: bool | None = None,
    ) -> ScheduledTask:
        """Async :meth:`update_task` (same mutual-exclusion rules for ``chat_id``)."""
        return await update_scheduled_task_async(
            user_id=self._user_id,
            company_id=self._company_id,
            task_id=task_id,
            cron_expression=cron_expression,
            assistant_id=assistant_id,
            prompt=prompt,
            chat_id=chat_id,
            clear_chat_id=clear_chat_id,
            enabled=enabled,
        )

    # ── Delete ────────────────────────────────────────────────────────────

    def delete_task(self, *, task_id: str) -> DeletedScheduledTask:
        """Permanently delete a scheduled task. This action cannot be undone."""
        return delete_scheduled_task(
            user_id=self._user_id,
            company_id=self._company_id,
            task_id=task_id,
        )

    async def delete_task_async(self, *, task_id: str) -> DeletedScheduledTask:
        """Async :meth:`delete_task`."""
        return await delete_scheduled_task_async(
            user_id=self._user_id,
            company_id=self._company_id,
            task_id=task_id,
        )

    # ── Convenience: enable/disable ───────────────────────────────────────

    def enable_task(self, *, task_id: str) -> ScheduledTask:
        """Re-enable a previously paused task (shortcut for ``update_task(..., enabled=True)``)."""
        return self.update_task(task_id=task_id, enabled=True)

    async def enable_task_async(self, *, task_id: str) -> ScheduledTask:
        """Async :meth:`enable_task`."""
        return await self.update_task_async(task_id=task_id, enabled=True)

    def disable_task(self, *, task_id: str) -> ScheduledTask:
        """Pause a task without deleting it (shortcut for ``update_task(..., enabled=False)``)."""
        return self.update_task(task_id=task_id, enabled=False)

    async def disable_task_async(self, *, task_id: str) -> ScheduledTask:
        """Async :meth:`disable_task`."""
        return await self.update_task_async(task_id=task_id, enabled=False)
