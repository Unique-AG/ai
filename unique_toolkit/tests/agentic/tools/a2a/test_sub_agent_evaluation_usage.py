import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.tools.a2a.evaluation.config import (
    SubAgentEvaluationConfig,
    SubAgentEvaluationServiceConfig,
)
from unique_toolkit.agentic.tools.a2a.evaluation.evaluator import (
    SubAgentEvaluationService,
    SubAgentEvaluationSpec,
)
from unique_toolkit.agentic.tools.a2a.response_watcher import SubAgentResponseWatcher
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelCompletionChoice,
    LanguageModelResponse,
    LanguageModelTokenUsage,
)


def _make_message(label: str) -> dict:
    return {
        "id": "msg-1",
        "chatId": "chat-1",
        "role": "ASSISTANT",
        "text": "some sub-agent answer",
        "assessment": [
            {
                "label": label,
                "status": ChatMessageAssessmentStatus.DONE,
                "explanation": "looks fine",
                "title": "Hallucination",
                "type": "HALLUCINATION",
            }
        ],
    }


def _make_service(complete_async_mock: AsyncMock) -> SubAgentEvaluationService:
    watcher = SubAgentResponseWatcher()
    watcher.notify_response(
        assistant_id="assistant-1",
        name="Agent One",
        sequence_number=1,
        response=_make_message(ChatMessageAssessmentLabel.GREEN),
        timestamp=datetime.datetime.now(datetime.UTC),
    )
    watcher.notify_response(
        assistant_id="assistant-2",
        name="Agent Two",
        sequence_number=1,
        response=_make_message(ChatMessageAssessmentLabel.GREEN),
        timestamp=datetime.datetime.now(datetime.UTC),
    )

    language_model_service = MagicMock()
    language_model_service.complete_async = complete_async_mock

    return SubAgentEvaluationService(
        config=SubAgentEvaluationServiceConfig(),
        language_model_service=language_model_service,
        response_watcher=watcher,
        evaluation_specs=[
            SubAgentEvaluationSpec(
                display_name="Agent One",
                assistant_id="assistant-1",
                config=SubAgentEvaluationConfig(),
            ),
            SubAgentEvaluationSpec(
                display_name="Agent Two",
                assistant_id="assistant-2",
                config=SubAgentEvaluationConfig(),
            ),
        ],
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_sub_agent_evaluation__multiple_assessments__carries_usage() -> None:
    """SubAgentEvaluationService.run(), in its multi-assessment branch, makes
    its own LLM call to summarize the assessments (_get_reason) — that
    response's usage was previously discarded (_get_reason returned only a
    plain str). Verify it now survives onto the final EvaluationMetricResult."""
    complete_async_mock = AsyncMock(
        return_value=LanguageModelResponse(
            choices=[
                LanguageModelCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": "summary text"},
                    finish_reason="stop",
                )
            ],
            usage=LanguageModelTokenUsage(
                completion_tokens=12, prompt_tokens=34, total_tokens=46
            ),
        )
    )
    service = _make_service(complete_async_mock)

    result = await service.run(loop_response=MagicMock())

    complete_async_mock.assert_awaited_once()
    assert result.reason == "summary text"
    assert result.usage == LanguageModelTokenUsage(
        completion_tokens=12, prompt_tokens=34, total_tokens=46
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_sub_agent_evaluation__no_responses__usage_none_no_llm_call() -> None:
    """The no-responses early-return path makes no LLM call at all --
    usage must stay None, and complete_async must never be called."""
    complete_async_mock = AsyncMock()
    watcher = SubAgentResponseWatcher()
    language_model_service = MagicMock()
    language_model_service.complete_async = complete_async_mock

    service = SubAgentEvaluationService(
        config=SubAgentEvaluationServiceConfig(),
        language_model_service=language_model_service,
        response_watcher=watcher,
        evaluation_specs=[
            SubAgentEvaluationSpec(
                display_name="Agent One",
                assistant_id="assistant-1",
                config=SubAgentEvaluationConfig(),
            )
        ],
    )

    result = await service.run(loop_response=MagicMock())

    complete_async_mock.assert_not_awaited()
    assert result.usage is None
