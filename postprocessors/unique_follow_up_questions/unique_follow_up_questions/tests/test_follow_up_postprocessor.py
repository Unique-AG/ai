from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_follow_up_questions.follow_up_postprocessor import FollowUpPostprocessor
from unique_follow_up_questions.schema import FollowUpQuestionsOutput


def _make_postprocessor(
    *, use_structured_output: bool, adapt_to_language: bool = True
) -> FollowUpPostprocessor:
    """Builds a FollowUpPostprocessor with only the attributes
    `_generate_follow_up_questions` touches, skipping the full constructor's
    heavy dependencies (ChatEvent, HistoryManager, ...)."""
    postprocessor = object.__new__(FollowUpPostprocessor)
    config = MagicMock()
    config.use_structured_output = use_structured_output
    config.adapt_to_language = adapt_to_language
    config.language_model.name = "gpt-4o"
    postprocessor._config = config  # type: ignore[attr-defined]
    postprocessor._logger = MagicMock()  # type: ignore[attr-defined]
    postprocessor._llm_service = AsyncMock()  # type: ignore[attr-defined]
    postprocessor._user_message_text = "Please answer in German."  # type: ignore[attr-defined]
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


def test_constructor_does_not_read_event_language() -> None:
    user_message = MagicMock(spec=["text"])
    user_message.text = "Bitte fasse das zusammen."
    event = MagicMock()
    event.payload.user_message = user_message

    postprocessor = FollowUpPostprocessor(
        logger=MagicMock(),
        config=FollowUpQuestionsConfig(),
        event=event,
        historyManager=MagicMock(),
        llm_service=MagicMock(),
    )

    assert postprocessor._user_message_text == "Bitte fasse das zusammen."


@pytest.mark.asyncio
async def test_detect_language_uses_request_and_renders_custom_language_placeholder() -> (
    None
):
    postprocessor = _make_postprocessor(use_structured_output=False)
    postprocessor._user_message_text = "Bitte antworte auf Japanisch."
    postprocessor._llm_service.complete_async.return_value = _make_response(
        content='{"language": "Japanese"}',
        usage=None,
    )

    language = await postprocessor._detect_language()
    request = postprocessor._llm_service.complete_async.await_args.kwargs
    detection_prompt = request["messages"].root[0].content

    assert language == "Japanese"
    assert "Bitte antworte auf Japanisch." in detection_prompt

    config = FollowUpQuestionsConfig(
        user_prompt="{{ conversation_history }}\nLanguage={{ language }}"
    )
    postprocessor._config = config
    postprocessor._generate_follow_up_questions = AsyncMock(
        return_value=FollowUpQuestionsOutput()
    )
    await postprocessor._get_follow_up_question_suggestion(
        language=language,
        language_model_service=MagicMock(),
        history=[],
    )
    follow_up_messages = postprocessor._generate_follow_up_questions.await_args.args[1]
    assert "Language=Japanese" in follow_up_messages.root[-1].content


@pytest.mark.asyncio
async def test_resolve_language_skips_detection_when_adaptation_is_disabled() -> None:
    postprocessor = _make_postprocessor(
        use_structured_output=False,
        adapt_to_language=False,
    )
    postprocessor._detect_language = AsyncMock()

    language = await postprocessor._resolve_language()

    assert language is None
    postprocessor._detect_language.assert_not_awaited()

    postprocessor._config = FollowUpQuestionsConfig(adapt_to_language=False)
    postprocessor._generate_follow_up_questions = AsyncMock(
        return_value=FollowUpQuestionsOutput()
    )
    await postprocessor._get_follow_up_question_suggestion(
        language=language,
        language_model_service=MagicMock(),
        history=[],
    )
    follow_up_messages = postprocessor._generate_follow_up_questions.await_args.args[1]
    assert (
        "Generate the follow-up questions in" not in follow_up_messages.root[-1].content
    )


@pytest.mark.asyncio
async def test_detect_language_falls_back_to_english_on_malformed_output() -> None:
    postprocessor = _make_postprocessor(use_structured_output=False)
    postprocessor._llm_service.complete_async.return_value = _make_response(
        content="not-json",
        usage=None,
    )

    language = await postprocessor._detect_language()

    assert language == "English"
    postprocessor._logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_language_detection_and_generation_record_separate_usage() -> None:
    postprocessor = _make_postprocessor(use_structured_output=False)
    detection_usage = LanguageModelTokenUsage(
        completion_tokens=2, prompt_tokens=8, total_tokens=10
    )
    generation_usage = LanguageModelTokenUsage(
        completion_tokens=10, prompt_tokens=20, total_tokens=30
    )
    postprocessor._llm_service.complete_async.side_effect = [
        _make_response(
            content='{"language": "German"}',
            usage=detection_usage,
        ),
        _make_response(
            content='{"questions": []}',
            usage=generation_usage,
        ),
    ]

    await postprocessor._detect_language()
    await postprocessor._generate_follow_up_questions(
        language_model_service=postprocessor._llm_service,
        messages=MagicMock(),
    )

    assert [stat.source for stat in postprocessor.invocation_stats] == [
        "follow_up_questions_language_detection",
        "follow_up_questions",
    ]
    assert [stat.token_usage for stat in postprocessor.invocation_stats] == [
        detection_usage,
        generation_usage,
    ]


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
