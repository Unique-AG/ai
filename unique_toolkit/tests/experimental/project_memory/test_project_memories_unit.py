"""Unit tests for :mod:`unique_toolkit.experimental.resources.project_memory`.

The SDK is patched at the ``unique_sdk.ProjectMemory`` boundary, so drift in
method names or arguments between toolkit and SDK shows up here.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.experimental.resources.project_memory import ProjectMemories

USER_ID = "user_1"
COMPANY_ID = "company_1"
PROJECT_ID = "custom_space_1"
DOCUMENT = "# Project memory\n\n## Decisions\n- Ship in two waves.\n"


def _chat_event(payload_extra: dict) -> ChatEvent:
    return ChatEvent.model_validate(
        {
            "id": "event1",
            "event": "unique.chat.external-module.chosen",
            "userId": USER_ID,
            "companyId": COMPANY_ID,
            "payload": {
                "name": "test_module",
                "description": "Test description",
                "configuration": {},
                "chatId": "chat_current",
                "assistantId": "assistant1",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
                **payload_extra,
            },
        }
    )


@pytest.mark.ai
def test_chat_event_reads_project_id_from_the_wire() -> None:
    assert _chat_event({"projectId": PROJECT_ID}).payload.project_id == PROJECT_ID


@pytest.mark.ai
def test_chat_event_without_project_id_defaults_to_none() -> None:
    assert _chat_event({}).payload.project_id is None


@pytest.mark.ai
def test_from_event_raises_for_a_chat_outside_a_project() -> None:
    with pytest.raises(ValueError, match="project_id"):
        ProjectMemories.from_event(_chat_event({}))


@pytest.mark.ai
def test_constructor_rejects_an_empty_project_id() -> None:
    with pytest.raises(ValueError):
        ProjectMemories(user_id=USER_ID, company_id=COMPANY_ID, project_id="")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_document_async_reads_as_the_event_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk = AsyncMock(return_value={"document": DOCUMENT, "state": "{}"})
    monkeypatch.setattr("unique_sdk.ProjectMemory.retrieve_async", sdk)

    service = ProjectMemories.from_event(_chat_event({"projectId": PROJECT_ID}))

    assert await service.get_document_async() == DOCUMENT
    sdk.assert_awaited_once_with(USER_ID, COMPANY_ID, PROJECT_ID)


@pytest.mark.ai
@pytest.mark.parametrize("document", [None, ""])
def test_get_document_is_none_before_the_first_write(
    monkeypatch: pytest.MonkeyPatch, document: str | None
) -> None:
    sdk = MagicMock(return_value={"document": document, "state": None})
    monkeypatch.setattr("unique_sdk.ProjectMemory.retrieve", sdk)

    service = ProjectMemories(
        user_id=USER_ID, company_id=COMPANY_ID, project_id=PROJECT_ID
    )

    assert service.get_document() is None
    sdk.assert_called_once_with(USER_ID, COMPANY_ID, PROJECT_ID)
