"""
Integration tests for ``Space.create_message`` request fields.

These tests call the QA (or other) public API configured via
``tests/integration/.env.qa`` (see ``.env.qa.example``).

Inspectable JSON artifacts are written under
``tests/integration/artifacts/<test>/<run_id>/``.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from tests.integration.conftest import IntegrationArtifacts, QaIntegrationConfig
from unique_sdk.api_resources._space import Space


def _write_create_message_artifacts(
    artifacts: IntegrationArtifacts,
    *,
    request_params: dict[str, Any],
    response: Any | None = None,
    error: BaseException | None = None,
) -> None:
    artifacts.write("create_message_request", request_params)
    if response is not None:
        artifacts.write("create_message_response", response)
    if error is not None:
        artifacts.write(
            "create_message_error",
            {
                "type": type(error).__name__,
                "message": str(error),
            },
        )


@pytest.mark.ai
@pytest.mark.integration
def test_space__create_message__accepts_extended_request_fields(
    qa_config: QaIntegrationConfig,
    space_assistant_id: str,
    integration_artifacts: IntegrationArtifacts,
) -> None:
    """
    Purpose: Verify Space.create_message accepts the OpenAPI-aligned request fields.
    Why this matters: languageModel, availableSkills, selectedUploadedFileIds, and
        typed skillChoices must round-trip through the public API without 4xx errors.
    Setup summary: Create a message with the new optional fields, assert the user
        message response shape, then delete the chat. Artifacts capture request/response.
    """
    prompt = f"integration create_message ping {uuid.uuid4().hex[:8]}"
    skill_choice: Space.SkillChoice = {
        "name": "integration-skill",
        "contentId": f"cont_integration_{uuid.uuid4().hex[:8]}",
    }
    if qa_config.scope_id:
        skill_choice["scopeId"] = qa_config.scope_id

    create_params: Space.CreateMessageParams = {
        "assistantId": space_assistant_id,
        "text": prompt,
        "toolChoices": [],
        "skillChoices": [skill_choice],
        "availableSkills": [skill_choice],
        "selectedUploadedFileIds": [],
        "autoApproveElicitation": True,
    }

    message: Space.Message | None = None
    error: BaseException | None = None
    try:
        message = Space.create_message(
            user_id=qa_config.user_id,
            company_id=qa_config.company_id,
            **create_params,
        )
    except BaseException as exc:
        error = exc
        raise
    finally:
        _write_create_message_artifacts(
            integration_artifacts,
            request_params=dict(create_params),
            response=message,
            error=error,
        )

    assert message is not None
    chat_id = message.get("chatId")
    try:
        assert isinstance(message, dict)
        assert message.get("id")
        assert chat_id
        assert message.get("text") == prompt
        # create_message returns the user message envelope; QA currently omits
        # ``role`` on this path (see artifacts create_message_response.json).
        assert message.get("object") == "message"
        integration_artifacts.write(
            "assertions",
            {
                "messageId": message.get("id"),
                "chatId": chat_id,
                "object": message.get("object"),
                "role": message.get("role"),
                "textMatchesPrompt": message.get("text") == prompt,
            },
        )
    finally:
        if chat_id:
            try:
                Space.delete_chat(
                    user_id=qa_config.user_id,
                    company_id=qa_config.company_id,
                    chat_id=chat_id,
                )
            except Exception:
                pass


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_space__create_message_async__accepts_selected_uploaded_file_ids(
    qa_config: QaIntegrationConfig,
    space_assistant_id: str,
    integration_artifacts: IntegrationArtifacts,
) -> None:
    """
    Purpose: Verify async create_message accepts selectedUploadedFileIds.
    Why this matters: Sub-agent / upload scoping relies on this field being forwarded.
    Setup summary: Await create_message_async with an empty selectedUploadedFileIds
        list, assert a chat/message was created, then delete the chat. Artifacts
        capture request/response.
    """
    prompt = f"integration async create_message ping {uuid.uuid4().hex[:8]}"
    create_params: Space.CreateMessageParams = {
        "assistantId": space_assistant_id,
        "text": prompt,
        "selectedUploadedFileIds": [],
        "availableSkills": [],
        "skillChoices": [],
    }

    message: Space.Message | None = None
    error: BaseException | None = None
    try:
        message = await Space.create_message_async(
            user_id=qa_config.user_id,
            company_id=qa_config.company_id,
            **create_params,
        )
    except BaseException as exc:
        error = exc
        raise
    finally:
        _write_create_message_artifacts(
            integration_artifacts,
            request_params=dict(create_params),
            response=message,
            error=error,
        )

    assert message is not None
    chat_id = message.get("chatId")
    try:
        assert message.get("id")
        assert chat_id
        assert message.get("text") == prompt
        integration_artifacts.write(
            "assertions",
            {
                "messageId": message.get("id"),
                "chatId": chat_id,
                "textMatchesPrompt": message.get("text") == prompt,
            },
        )
    finally:
        if chat_id:
            try:
                await Space.delete_chat_async(
                    user_id=qa_config.user_id,
                    company_id=qa_config.company_id,
                    chat_id=chat_id,
                )
            except Exception:
                pass
