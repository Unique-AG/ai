"""Low-level function wrappers around :class:`unique_sdk.ScheduledTask`.

Each SDK operation gets a ``<verb>`` and ``<verb>_async`` pair. The functions
take ``user_id`` and ``company_id`` as the first two positional arguments (the
acting user's credentials) and return toolkit Pydantic models — SDK
``TypedDict``\\s never leak out of this module.

Notes on update semantics
-------------------------

:func:`update_scheduled_task` / :func:`update_scheduled_task_async` support two
mutually-exclusive intents for :attr:`chat_id`:

- Pass ``chat_id="chat_…"`` to repoint the task at a different chat.
- Pass ``clear_chat_id=True`` to drop the current link (the SDK sends
  ``chatId=None`` on the wire; the server then spawns a fresh chat on every
  trigger).
- Omit both to leave the current chat setting untouched.

Mixing them raises :class:`TypeError` before the SDK call.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The API
    may change without notice.
"""

from __future__ import annotations

import asyncio
from typing import Any

import unique_sdk

from unique_toolkit.experimental.scheduled_task.schemas import (
    DeletedScheduledTask,
    ScheduledTask,
)


def create_scheduled_task(
    user_id: str,
    company_id: str,
    *,
    cron_expression: str,
    assistant_id: str,
    prompt: str,
    chat_id: str | None = None,
    enabled: bool = True,
) -> ScheduledTask:
    """Create a new cron-based scheduled task.

    Args:
        user_id: Acting user (SDK requirement).
        company_id: Owning company (SDK requirement).
        cron_expression: 5-field UTC cron expression (``"m h dom mon dow"``).
        assistant_id: Assistant id to execute on every trigger.
        prompt: Prompt text sent to the assistant on each run.
        chat_id: Optional chat to continue; ``None`` (default) means a fresh
            chat is created every run.
        enabled: Whether the task is active from creation. Defaults to
            ``True`` so tasks fire as soon as they are registered; pass
            ``False`` to stage a task that can be enabled later via
            :func:`update_scheduled_task`.

    Returns:
        The created :class:`ScheduledTask` as echoed by the server.
    """
    params: dict[str, Any] = {
        "cronExpression": cron_expression,
        "assistantId": assistant_id,
        "prompt": prompt,
        "enabled": enabled,
    }
    if chat_id is not None:
        params["chatId"] = chat_id

    payload = unique_sdk.ScheduledTask.create(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return ScheduledTask.model_validate(payload, by_alias=True, by_name=True)


async def create_scheduled_task_async(
    user_id: str,
    company_id: str,
    *,
    cron_expression: str,
    assistant_id: str,
    prompt: str,
    chat_id: str | None = None,
    enabled: bool = True,
) -> ScheduledTask:
    """Async :func:`create_scheduled_task`."""
    params: dict[str, Any] = {
        "cronExpression": cron_expression,
        "assistantId": assistant_id,
        "prompt": prompt,
        "enabled": enabled,
    }
    if chat_id is not None:
        params["chatId"] = chat_id

    payload = await unique_sdk.ScheduledTask.create_async(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return ScheduledTask.model_validate(payload, by_alias=True, by_name=True)


def list_scheduled_tasks(user_id: str, company_id: str) -> list[ScheduledTask]:
    """List every scheduled task visible to the acting user."""
    result = unique_sdk.ScheduledTask.list(user_id=user_id, company_id=company_id)
    return [
        ScheduledTask.model_validate(task, by_alias=True, by_name=True)
        for task in result
    ]


async def list_scheduled_tasks_async(
    user_id: str, company_id: str
) -> list[ScheduledTask]:
    """Async :func:`list_scheduled_tasks`."""
    result = await unique_sdk.ScheduledTask.list_async(
        user_id=user_id, company_id=company_id
    )
    return [
        ScheduledTask.model_validate(task, by_alias=True, by_name=True)
        for task in result
    ]


def get_scheduled_task(
    user_id: str,
    company_id: str,
    *,
    task_id: str,
) -> ScheduledTask:
    """Fetch the full detail of a single scheduled task by id."""
    payload = unique_sdk.ScheduledTask.retrieve(
        user_id=user_id,
        company_id=company_id,
        id=task_id,
    )
    return ScheduledTask.model_validate(payload, by_alias=True, by_name=True)


async def get_scheduled_task_async(
    user_id: str,
    company_id: str,
    *,
    task_id: str,
) -> ScheduledTask:
    """Async :func:`get_scheduled_task`."""
    payload = await unique_sdk.ScheduledTask.retrieve_async(
        user_id=user_id,
        company_id=company_id,
        id=task_id,
    )
    return ScheduledTask.model_validate(payload, by_alias=True, by_name=True)


def update_scheduled_task(
    user_id: str,
    company_id: str,
    *,
    task_id: str,
    cron_expression: str | None = None,
    assistant_id: str | None = None,
    prompt: str | None = None,
    chat_id: str | None = None,
    clear_chat_id: bool = False,
    enabled: bool | None = None,
) -> ScheduledTask:
    """Update an existing scheduled task (server-side partial update).

    Only the keyword arguments you pass are sent to the API; everything else is
    left untouched. Pass ``clear_chat_id=True`` to remove the current chat link
    (``chatId=None`` on the wire) — the server will then spin up a brand-new
    chat on every future trigger.

    Raises:
        TypeError: If ``chat_id`` and ``clear_chat_id=True`` are combined.
    """
    params = _build_update_params(
        cron_expression=cron_expression,
        assistant_id=assistant_id,
        prompt=prompt,
        chat_id=chat_id,
        clear_chat_id=clear_chat_id,
        enabled=enabled,
    )
    payload = unique_sdk.ScheduledTask.modify(
        user_id=user_id,
        company_id=company_id,
        id=task_id,
        **params,
    )
    return ScheduledTask.model_validate(payload, by_alias=True, by_name=True)


async def update_scheduled_task_async(
    user_id: str,
    company_id: str,
    *,
    task_id: str,
    cron_expression: str | None = None,
    assistant_id: str | None = None,
    prompt: str | None = None,
    chat_id: str | None = None,
    clear_chat_id: bool = False,
    enabled: bool | None = None,
) -> ScheduledTask:
    """Async :func:`update_scheduled_task`."""
    params = _build_update_params(
        cron_expression=cron_expression,
        assistant_id=assistant_id,
        prompt=prompt,
        chat_id=chat_id,
        clear_chat_id=clear_chat_id,
        enabled=enabled,
    )
    payload = await unique_sdk.ScheduledTask.modify_async(
        user_id=user_id,
        company_id=company_id,
        id=task_id,
        **params,
    )
    return ScheduledTask.model_validate(payload, by_alias=True, by_name=True)


def delete_scheduled_task(
    user_id: str,
    company_id: str,
    *,
    task_id: str,
) -> DeletedScheduledTask:
    """Permanently delete a scheduled task. This action cannot be undone."""
    payload = unique_sdk.ScheduledTask.delete(
        user_id=user_id,
        company_id=company_id,
        id=task_id,
    )
    return DeletedScheduledTask.model_validate(payload, by_alias=True, by_name=True)


async def delete_scheduled_task_async(
    user_id: str,
    company_id: str,
    *,
    task_id: str,
) -> DeletedScheduledTask:
    """Async :func:`delete_scheduled_task`.

    Falls back to :func:`asyncio.to_thread` if the SDK method does not provide
    an ``_async`` variant, so the event loop is never blocked.
    """
    sdk_async = getattr(unique_sdk.ScheduledTask, "delete_async", None)
    if sdk_async is None:
        return await asyncio.to_thread(
            delete_scheduled_task,
            user_id,
            company_id,
            task_id=task_id,
        )
    payload = await sdk_async(
        user_id=user_id,
        company_id=company_id,
        id=task_id,
    )
    return DeletedScheduledTask.model_validate(payload, by_alias=True, by_name=True)


def _build_update_params(
    *,
    cron_expression: str | None,
    assistant_id: str | None,
    prompt: str | None,
    chat_id: str | None,
    clear_chat_id: bool,
    enabled: bool | None,
) -> dict[str, Any]:
    """Translate toolkit kwargs into the SDK ``ScheduledTask.ModifyParams`` shape.

    Fields that were not provided are omitted entirely (partial update). The
    ``chat_id`` / ``clear_chat_id`` pair is mutually exclusive; passing both is
    a usage error and raises :class:`TypeError` here — never at the SDK layer.
    """
    if chat_id is not None and clear_chat_id:
        raise TypeError(
            "update_scheduled_task: pass either chat_id= to set a new chat or "
            "clear_chat_id=True to clear it, not both."
        )

    params: dict[str, Any] = {}
    if cron_expression is not None:
        params["cronExpression"] = cron_expression
    if assistant_id is not None:
        params["assistantId"] = assistant_id
    if prompt is not None:
        params["prompt"] = prompt
    if chat_id is not None:
        params["chatId"] = chat_id
    elif clear_chat_id:
        params["chatId"] = None
    if enabled is not None:
        params["enabled"] = enabled
    return params
