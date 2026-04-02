"""Scheduled tasks commands: create, list, get, update, delete cron-based tasks."""

from __future__ import annotations

import unique_sdk
from unique_sdk.cli.formatting import format_scheduled_task, format_scheduled_tasks
from unique_sdk.cli.state import ShellState


def cmd_schedule_list(state: ShellState) -> str:
    """List all scheduled tasks for the authenticated user."""
    try:
        tasks = unique_sdk.ScheduledTask.list(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
        )
        return format_scheduled_tasks(tasks)
    except unique_sdk.APIError as e:
        return f"schedule: {e}"


def cmd_schedule_get(state: ShellState, task_id: str) -> str:
    """Get details of a single scheduled task by ID."""
    try:
        task = unique_sdk.ScheduledTask.retrieve(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            id=task_id,
        )
        return format_scheduled_task(task)
    except unique_sdk.APIError as e:
        return f"schedule: {e}"


def cmd_schedule_create(
    state: ShellState,
    cron: str,
    assistant_id: str,
    prompt: str,
    *,
    chat_id: str | None = None,
    enabled: bool = True,
) -> str:
    """Create a new scheduled task."""
    try:
        params: dict = {
            "cronExpression": cron,
            "assistantId": assistant_id,
            "prompt": prompt,
            "enabled": enabled,
        }
        if chat_id is not None:
            params["chatId"] = chat_id

        task = unique_sdk.ScheduledTask.create(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )
        task_id = getattr(task, "id", "?")
        return f"Created scheduled task {task_id}\n\n{format_scheduled_task(task)}"
    except unique_sdk.APIError as e:
        return f"schedule: {e}"


def cmd_schedule_update(
    state: ShellState,
    task_id: str,
    *,
    cron: str | None = None,
    assistant_id: str | None = None,
    prompt: str | None = None,
    chat_id: str | None = None,
    enabled: bool | None = None,
) -> str:
    """Update an existing scheduled task."""
    try:
        params: dict = {}
        if cron is not None:
            params["cronExpression"] = cron
        if assistant_id is not None:
            params["assistantId"] = assistant_id
        if prompt is not None:
            params["prompt"] = prompt
        if chat_id is not None:
            params["chatId"] = chat_id
        if enabled is not None:
            params["enabled"] = enabled

        if not params:
            return "schedule: nothing to update (provide at least one option)"

        task = unique_sdk.ScheduledTask.modify(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            id=task_id,
            **params,
        )
        return f"Updated scheduled task {task_id}\n\n{format_scheduled_task(task)}"
    except unique_sdk.APIError as e:
        return f"schedule: {e}"


def cmd_schedule_delete(state: ShellState, task_id: str) -> str:
    """Delete a scheduled task by ID."""
    try:
        result = unique_sdk.ScheduledTask.delete(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            id=task_id,
        )
        deleted_id = result.get("id", task_id) if hasattr(result, "get") else task_id
        return f"Deleted scheduled task {deleted_id}"
    except unique_sdk.APIError as e:
        return f"schedule: {e}"
