"""Tests that HallucinationEvaluation grounds against non-chunk context.

UN-21951: external context texts (e.g. MCP tool output) registered on the
ReferenceManager must be appended to the evaluation context — in addition to
chunk-derived context, capped by ``max_external_context_chars_per_source`` —
without being converted to ContentChunks.
"""

from types import SimpleNamespace

import pytest

from unique_toolkit.agentic.evaluation.hallucination import (
    hallucination_evaluation as he,
)
from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
    SourceSelectionMode,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.agentic.reference_manager.reference_manager import (
    ReferenceManager,
)
from unique_toolkit.chat.schemas import ChatMessageRole
from unique_toolkit.language_model.schemas import (
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
)


def _make_event() -> SimpleNamespace:
    return SimpleNamespace(
        company_id="company_1",
        user_id="user_1",
        payload=SimpleNamespace(
            user_message=SimpleNamespace(text="what is ACME revenue?"),
        ),
    )


def _make_response(text: str = "ACME revenue is 1M.") -> LanguageModelStreamResponse:
    return LanguageModelStreamResponse(
        message=LanguageModelStreamResponseMessage(
            id="msg_1",
            previous_message_id=None,
            role=ChatMessageRole.ASSISTANT,
            text=text,
            chat_id="chat_1",
            original_text=text,
            references=None,
        ),
        tool_calls=None,
    )


@pytest.fixture
def captured_context(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch check_hallucination to capture the context_texts it receives."""
    captured: dict = {}

    async def _fake_check_hallucination(*, company_id, user_id, input, config):
        captured["context_texts"] = list(input.context_texts or [])
        return EvaluationMetricResult(
            name=EvaluationMetricName.HALLUCINATION,
            value="LOW",
            reason="grounded",
        )

    monkeypatch.setattr(he, "check_hallucination", _fake_check_hallucination)
    return captured


async def test_external_context_is_appended(captured_context: dict) -> None:
    manager = ReferenceManager()
    manager.add_external_context_texts(["ACME revenue: 1M"])
    evaluation = he.HallucinationEvaluation(
        HallucinationConfig(source_selection_mode=SourceSelectionMode.FROM_IDS),
        _make_event(),  # type: ignore[arg-type]
        manager,
    )

    result = await evaluation.run(_make_response())

    # No chunks → context comes solely from the external (MCP) source.
    assert captured_context["context_texts"] == ["ACME revenue: 1M"]
    assert result.value == "LOW"
    assert result.is_positive is True


async def test_external_context_is_truncated(captured_context: dict) -> None:
    manager = ReferenceManager()
    manager.add_external_context_texts(["x" * 100])
    evaluation = he.HallucinationEvaluation(
        HallucinationConfig(
            source_selection_mode=SourceSelectionMode.FROM_IDS,
            max_external_context_chars_per_source=10,
        ),
        _make_event(),  # type: ignore[arg-type]
        manager,
    )

    await evaluation.run(_make_response())

    assert captured_context["context_texts"] == ["x" * 10]


async def test_no_external_context_preserves_chunk_only_behaviour(
    captured_context: dict,
) -> None:
    manager = ReferenceManager()  # no chunks, no external context
    evaluation = he.HallucinationEvaluation(
        HallucinationConfig(source_selection_mode=SourceSelectionMode.FROM_IDS),
        _make_event(),  # type: ignore[arg-type]
        manager,
    )

    await evaluation.run(_make_response())

    assert captured_context["context_texts"] == []
