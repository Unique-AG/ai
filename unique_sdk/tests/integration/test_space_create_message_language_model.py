"""
Integration tests for per-message ``languageModel`` on ``Space.create_message``.

Model group names are hardcoded below (not secrets). Assistant replies are
persisted under ``artifacts/<test>/<run_id>/`` for manual inspection
(``assistant_answer.txt``, ``assistant_message.json``, ``llm_invocations.json``).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.integration.conftest import IntegrationArtifacts, QaIntegrationConfig
from unique_sdk.utils.chat_in_space import (
    get_message_invocations,
    send_message_and_wait_for_completion,
)

# Public model group names exercised against QA (not credentials).
LANGUAGE_MODELS_UNDER_TEST = (
    "AZURE_GPT_54_2026_0305",
    "AZURE_GPT_5_MINI_2025_0807",
)


def _model_names(invocations: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for entry in invocations:
        model_name = entry.get("modelName")
        if isinstance(model_name, str) and model_name:
            names.append(model_name)
    return names


def _requested_model_matched(requested: str, model_names: list[str]) -> bool:
    """True if any invocation modelName equals or contains the requested group name."""
    requested_norm = requested.casefold()
    for name in model_names:
        name_norm = name.casefold()
        if requested_norm == name_norm or requested_norm in name_norm:
            return True
    return False


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("language_model", LANGUAGE_MODELS_UNDER_TEST)
async def test_space__create_message__language_model_override_completes_and_persists_answer(
    qa_config: QaIntegrationConfig,
    space_assistant_id: str,
    language_model: str,
    integration_artifacts: IntegrationArtifacts,
) -> None:
    """
    Purpose: Verify languageModel is accepted and the assistant completes a reply.
    Why this matters: Per-message model override must reach the orchestrator and
        produce a usable answer callers can inspect.
    Setup summary: Ask the model which model it is with a hardcoded languageModel,
        wait for completion + llm_invocations, persist answer artifacts for manual review.
    """
    prompt = (
        "What language model are you? Reply with your model name/version only "
        "in one short sentence. Do not use tools."
    )
    request_snapshot = {
        "assistantId": space_assistant_id,
        "text": prompt,
        "languageModel": language_model,
        "toolChoices": [],
        "autoApproveElicitation": True,
    }
    integration_artifacts.write("create_message_request", request_snapshot)

    try:
        answer = await send_message_and_wait_for_completion(
            user_id=qa_config.user_id,
            company_id=qa_config.company_id,
            assistant_id=space_assistant_id,
            text=prompt,
            tool_choices=[],
            language_model=language_model,
            auto_approve_elicitation=True,
            max_wait=120.0,
            wait_for_invocations=True,
        )
    except BaseException as exc:
        integration_artifacts.write(
            "create_message_error",
            {"type": type(exc).__name__, "message": str(exc)},
        )
        raise

    answer_text = answer.get("text") or ""
    invocations = get_message_invocations(answer)
    model_names = _model_names(invocations)
    chat_id = answer.get("chatId")

    integration_artifacts.write("assistant_message", answer)
    integration_artifacts.write_text("assistant_answer", answer_text)
    integration_artifacts.write("llm_invocations", invocations)
    integration_artifacts.write(
        "manual_inspection",
        {
            "chatId": chat_id,
            "assistantMessageId": answer.get("id"),
            "triggeringUserMessageId": answer.get("triggeringUserMessageId"),
            "requestedLanguageModel": language_model,
            "observedModelNames": model_names,
            "modelSelfIdentification": answer_text.strip(),
            "assistantAnswerPath": str(
                integration_artifacts.directory / "assistant_answer.txt"
            ),
            "note": (
                "Compare modelSelfIdentification / assistant_answer.txt with "
                "requestedLanguageModel and observedModelNames (llm_invocations). "
                "Chat is left undeleted when using UNIQUE_ASSISTANT_ID."
            ),
        },
    )

    assert chat_id
    assert answer_text.strip(), "assistant returned an empty answer"
    assert invocations, (
        "expected llm_invocations on the completed message; "
        "check llm_invocations.json / assistant_message.json"
    )
    assert _requested_model_matched(language_model, model_names), (
        f"requested languageModel={language_model!r} not reflected in "
        f"invocation modelNames={model_names!r}"
    )
