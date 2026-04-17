"""Unit tests for :class:`unique_toolkit.experimental.scheduled_task.ScheduledTasks`.

The SDK is patched at the ``unique_sdk.ScheduledTask`` boundary so we notice any
drift in method names or wire-level field names between toolkit and SDK.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.experimental.scheduled_task import (
    DeletedScheduledTask,
    ScheduledTask,
    ScheduledTasks,
)

SAMPLE_TASK: dict = {
    "id": "task_abc123",
    "object": "scheduled_task",
    "cronExpression": "0 9 * * 1-5",
    "assistantId": "assistant_xyz",
    "assistantName": "Daily Reporter",
    "chatId": None,
    "prompt": "Generate the daily report",
    "enabled": True,
    "lastRunAt": None,
    "createdAt": "2026-04-17T08:00:00Z",
    "updatedAt": "2026-04-17T08:00:00Z",
}

SAMPLE_DELETED: dict = {
    "id": "task_abc123",
    "object": "scheduled_task",
    "deleted": True,
}


@pytest.fixture
def service() -> ScheduledTasks:
    """Service bound to fixed test credentials."""
    return ScheduledTasks(company_id="company_1", user_id="user_1")


# ── Create ────────────────────────────────────────────────────────────────────


def test_AI_create_task_passes_required_fields_to_sdk(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """create_task translates toolkit snake_case kwargs into camelCase SDK params."""
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SAMPLE_TASK

    monkeypatch.setattr("unique_sdk.ScheduledTask.create", fake_create)

    result = service.create_task(
        cron_expression="0 9 * * 1-5",
        assistant_id="assistant_xyz",
        prompt="Generate the daily report",
    )

    assert captured["user_id"] == "user_1"
    assert captured["company_id"] == "company_1"
    assert captured["cronExpression"] == "0 9 * * 1-5"
    assert captured["assistantId"] == "assistant_xyz"
    assert captured["prompt"] == "Generate the daily report"
    assert "chatId" not in captured
    assert captured["enabled"] is True
    assert isinstance(result, ScheduledTask)
    assert result.id == "task_abc123"


def test_AI_create_task_forwards_optional_chat_id_and_disabled_flag(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """Optional chat_id is only forwarded when explicitly provided, and enabled=False is sent through."""
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return {**SAMPLE_TASK, "chatId": "chat_abc", "enabled": False}

    monkeypatch.setattr("unique_sdk.ScheduledTask.create", fake_create)

    result = service.create_task(
        cron_expression="*/15 * * * *",
        assistant_id="assistant_xyz",
        prompt="Poll support tickets",
        chat_id="chat_abc",
        enabled=False,
    )

    assert captured["chatId"] == "chat_abc"
    assert captured["enabled"] is False
    assert result.chat_id == "chat_abc"
    assert result.enabled is False


# ── List / get / delete ───────────────────────────────────────────────────────


def test_AI_list_tasks_returns_parsed_models(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """list_tasks hands the SDK user+company and parses each task into a model."""
    fake = MagicMock(return_value=[SAMPLE_TASK, SAMPLE_TASK])
    monkeypatch.setattr("unique_sdk.ScheduledTask.list", fake)

    result = service.list_tasks()

    fake.assert_called_once_with(user_id="user_1", company_id="company_1")
    assert len(result) == 2
    assert all(isinstance(task, ScheduledTask) for task in result)


def test_AI_get_task_routes_id_to_sdk_id(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """get_task(task_id=...) hits the retrieve endpoint with id=<task_id>."""
    fake = MagicMock(return_value=SAMPLE_TASK)
    monkeypatch.setattr("unique_sdk.ScheduledTask.retrieve", fake)

    result = service.get_task(task_id="task_abc123")

    fake.assert_called_once_with(
        user_id="user_1", company_id="company_1", id="task_abc123"
    )
    assert result.id == "task_abc123"


def test_AI_delete_task_returns_deleted_payload(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """delete_task surfaces the DeletedScheduledTask model the API returns."""
    fake = MagicMock(return_value=SAMPLE_DELETED)
    monkeypatch.setattr("unique_sdk.ScheduledTask.delete", fake)

    result = service.delete_task(task_id="task_abc123")

    fake.assert_called_once_with(
        user_id="user_1", company_id="company_1", id="task_abc123"
    )
    assert isinstance(result, DeletedScheduledTask)
    assert result.deleted is True


# ── Update ────────────────────────────────────────────────────────────────────


def test_AI_update_task_only_forwards_fields_that_were_set(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """update_task omits untouched fields so the server-side partial update is respected."""
    captured: dict = {}

    def fake_modify(**kwargs):
        captured.update(kwargs)
        return {**SAMPLE_TASK, "enabled": False}

    monkeypatch.setattr("unique_sdk.ScheduledTask.modify", fake_modify)

    service.update_task(task_id="task_abc123", enabled=False)

    assert captured["id"] == "task_abc123"
    assert captured["enabled"] is False
    assert "cronExpression" not in captured
    assert "assistantId" not in captured
    assert "prompt" not in captured
    assert "chatId" not in captured


def test_AI_update_task_clear_chat_id_sends_null(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """clear_chat_id=True translates to chatId=None on the wire (server clears the link)."""
    captured: dict = {}

    def fake_modify(**kwargs):
        captured.update(kwargs)
        return SAMPLE_TASK

    monkeypatch.setattr("unique_sdk.ScheduledTask.modify", fake_modify)

    service.update_task(task_id="task_abc123", clear_chat_id=True)

    assert "chatId" in captured
    assert captured["chatId"] is None


def test_AI_update_task_rejects_mixed_chat_id_and_clear_flag(
    service: ScheduledTasks,
) -> None:
    """Passing chat_id= together with clear_chat_id=True raises TypeError before the SDK call."""
    with pytest.raises(TypeError, match="chat_id=|clear_chat_id="):
        service.update_task(
            task_id="task_abc123",
            chat_id="chat_new",
            clear_chat_id=True,
        )


# ── Enable / disable shortcuts ────────────────────────────────────────────────


def test_AI_disable_task_sends_enabled_false(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """disable_task is a shortcut that sends enabled=False through modify."""
    captured: dict = {}

    def fake_modify(**kwargs):
        captured.update(kwargs)
        return {**SAMPLE_TASK, "enabled": False}

    monkeypatch.setattr("unique_sdk.ScheduledTask.modify", fake_modify)

    service.disable_task(task_id="task_abc123")

    assert captured["enabled"] is False


def test_AI_enable_task_sends_enabled_true(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """enable_task is a shortcut that sends enabled=True through modify."""
    captured: dict = {}

    def fake_modify(**kwargs):
        captured.update(kwargs)
        return SAMPLE_TASK

    monkeypatch.setattr("unique_sdk.ScheduledTask.modify", fake_modify)

    service.enable_task(task_id="task_abc123")

    assert captured["enabled"] is True


# ── Async variants ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_AI_create_task_async_awaits_sdk_async(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """The async variant awaits unique_sdk.ScheduledTask.create_async."""
    fake = AsyncMock(return_value=SAMPLE_TASK)
    monkeypatch.setattr("unique_sdk.ScheduledTask.create_async", fake)

    result = await service.create_task_async(
        cron_expression="0 9 * * 1-5",
        assistant_id="assistant_xyz",
        prompt="Generate the daily report",
    )

    fake.assert_awaited_once()
    assert isinstance(result, ScheduledTask)


@pytest.mark.asyncio
async def test_AI_update_task_async_clear_chat_id_sends_null(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """Async update mirrors the sync clear-chat behaviour (chatId=None on the wire)."""
    captured: dict = {}

    async def fake_modify_async(**kwargs):
        captured.update(kwargs)
        return SAMPLE_TASK

    monkeypatch.setattr("unique_sdk.ScheduledTask.modify_async", fake_modify_async)

    await service.update_task_async(task_id="task_abc123", clear_chat_id=True)

    assert captured["chatId"] is None


@pytest.mark.asyncio
async def test_AI_list_tasks_async_awaits_sdk(
    monkeypatch: pytest.MonkeyPatch, service: ScheduledTasks
) -> None:
    """list_tasks_async awaits the SDK list_async and parses each task."""
    fake = AsyncMock(return_value=[SAMPLE_TASK])
    monkeypatch.setattr("unique_sdk.ScheduledTask.list_async", fake)

    result = await service.list_tasks_async()

    fake.assert_awaited_once_with(user_id="user_1", company_id="company_1")
    assert len(result) == 1
    assert isinstance(result[0], ScheduledTask)


# ── Response schema ───────────────────────────────────────────────────────────


def test_AI_scheduled_task_schema_preserves_cron_string_from_sdk() -> None:
    """ScheduledTask keeps cron_expression as the raw wire string so compound patterns survive."""
    task = ScheduledTask.model_validate(SAMPLE_TASK, by_alias=True, by_name=True)

    assert task.cron_expression == "0 9 * * 1-5"


def test_AI_scheduled_task_schema_round_trips_compound_cron_string() -> None:
    """A compound cron string from the server round-trips unchanged through model_dump(by_alias=True)."""
    task = ScheduledTask.model_validate(SAMPLE_TASK, by_alias=True, by_name=True)

    dumped = task.model_dump(by_alias=True)

    assert dumped["cronExpression"] == "0 9 * * 1-5"
