from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_follow_up_questions.follow_up_postprocessor import FollowUpPostprocessor


def _make_postprocessor(*, use_structured_output: bool) -> FollowUpPostprocessor:
    """Builds a FollowUpPostprocessor with only the attributes
    `_generate_follow_up_questions` touches, skipping the full constructor's
    heavy dependencies (ChatEvent, HistoryManager, ...)."""
    postprocessor = object.__new__(FollowUpPostprocessor)
    config = MagicMock()
    config.use_structured_output = use_structured_output
    config.language_model.name = "gpt-4o"
    postprocessor._config = config  # type: ignore[attr-defined]
    postprocessor._logger = MagicMock()  # type: ignore[attr-defined]
    postprocessor._invocation_stats = []  # type: ignore[attr-defined]
    return postprocessor


def _make_response(
    *, content: object, usage: LanguageModelTokenUsage | None
) -> MagicMock:
    response = MagicMock()
    response.usage = usage
    response.choices[0].message.content = content
    response.choices[0].message.parsed = content
    return response


@pytest.mark.asyncio
async def test_generate_follow_up_questions__non_string_content__usage_still_captured() -> (
    None
):
    """Tokens are spent even if the model's response content is not a string
    (non-structured path) -- the usage must still be recorded even though
    question generation itself falls back to an empty result."""
    postprocessor = _make_postprocessor(use_structured_output=False)
    usage = LanguageModelTokenUsage(
        completion_tokens=10, prompt_tokens=20, total_tokens=30
    )
    llm_service = AsyncMock()
    llm_service.complete_async = AsyncMock(
        return_value=_make_response(content=None, usage=usage)
    )

    result = await postprocessor._generate_follow_up_questions(
        language_model_service=llm_service,
        messages=MagicMock(),
    )

    assert result.questions == []
    assert len(postprocessor.invocation_stats) == 1
    assert postprocessor.invocation_stats[0].token_usage == usage


@pytest.mark.asyncio
async def test_generate_follow_up_questions__json_parse_failure__usage_still_captured() -> (
    None
):
    """Same as above, but the failure is JSON-parsing valid string content
    that isn't valid JSON."""
    postprocessor = _make_postprocessor(use_structured_output=False)
    usage = LanguageModelTokenUsage(
        completion_tokens=5, prompt_tokens=15, total_tokens=20
    )
    llm_service = AsyncMock()
    llm_service.complete_async = AsyncMock(
        return_value=_make_response(content="not-json{{{", usage=usage)
    )

    result = await postprocessor._generate_follow_up_questions(
        language_model_service=llm_service,
        messages=MagicMock(),
    )

    assert result.questions == []
    assert len(postprocessor.invocation_stats) == 1
    assert postprocessor.invocation_stats[0].token_usage == usage


@pytest.mark.asyncio
async def test_generate_follow_up_questions__success__usage_captured_once() -> None:
    postprocessor = _make_postprocessor(use_structured_output=False)
    usage = LanguageModelTokenUsage(
        completion_tokens=5, prompt_tokens=15, total_tokens=20
    )
    llm_service = AsyncMock()
    content = '{"questions": [{"category": "clarification", "question": "a?"}]}'
    llm_service.complete_async = AsyncMock(
        return_value=_make_response(content=content, usage=usage)
    )

    result = await postprocessor._generate_follow_up_questions(
        language_model_service=llm_service,
        messages=MagicMock(),
    )

    assert [q.question for q in result.questions] == ["a?"]
    assert len(postprocessor.invocation_stats) == 1
    assert postprocessor.invocation_stats[0].token_usage == usage
