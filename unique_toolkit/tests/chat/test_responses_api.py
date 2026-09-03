"""Tests for responses_api.py JSON parsing functionality."""

from unittest.mock import AsyncMock, patch

import pytest
import unique_sdk

from unique_toolkit.chat.responses_api import (
    _prepare_responses_args,
    _prepare_responses_params_util,
    _responses_stream_with_rate_limit_retry,
    convert_messages_to_openai,
    extract_reasoning_from_options,
    extract_verbosity_from_options,
    rate_limit_retry_config,
    strip_translated_responses_options,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)

# ============================================================================
# Tests for extract_reasoning_from_options
# ============================================================================


@pytest.mark.ai
def test_extract_reasoning__parses_json_string__correctly() -> None:
    """
    Purpose: Verify reasoning parameter is parsed from JSON string (UI compatibility).
    Why this matters: UI sends reasoning as JSON string due to limitations.
    Setup summary: Pass reasoning as JSON string, verify it's parsed to dict.
    """
    # Arrange
    options = {"reasoning": '{"effort": "high"}'}

    # Act
    result = extract_reasoning_from_options(options)

    # Assert
    assert result is not None
    assert result["effort"] == "high"


@pytest.mark.ai
def test_extract_reasoning__handles_dict__correctly() -> None:
    """
    Purpose: Verify reasoning parameter works with dict input (non-UI clients).
    Why this matters: Direct API calls pass reasoning as dict.
    Setup summary: Pass reasoning as dict, verify it's returned correctly.
    """
    # Arrange
    options = {"reasoning": {"effort": "low"}}

    # Act
    result = extract_reasoning_from_options(options)

    # Assert
    assert result is not None
    assert result["effort"] == "low"


@pytest.mark.ai
def test_extract_reasoning__handles_invalid_json__gracefully() -> None:
    """
    Purpose: Verify invalid JSON string doesn't crash, logs warning.
    Why this matters: Malformed input must not break the API pipeline.
    Setup summary: Pass invalid JSON, verify None returned (failsafe).
    """
    # Arrange
    options = {"reasoning": '{"invalid": json}'}

    # Act
    result = extract_reasoning_from_options(options)

    # Assert
    # Function has @failsafe decorator, should return None for invalid input
    assert result is None


@pytest.mark.ai
def test_extract_reasoning__returns_none__when_missing() -> None:
    """
    Purpose: Verify function returns None when reasoning not in options.
    Why this matters: Optional parameters must not cause errors.
    Setup summary: Pass options without reasoning, verify None returned.
    """
    # Arrange
    options = {"temperature": 0.7}

    # Act
    result = extract_reasoning_from_options(options)

    # Assert
    assert result is None


# ============================================================================
# Tests for extract_verbosity_from_options
# ============================================================================


@pytest.mark.ai
def test_extract_verbosity__parses_json_string__correctly() -> None:
    """
    Purpose: Verify text config is parsed from JSON string (UI compatibility).
    Why this matters: UI sends text config as JSON string due to limitations.
    Setup summary: Pass text as JSON string, verify it's parsed to dict.
    """
    # Arrange
    options = {"text": '{"verbosity": "high"}'}

    # Act
    result = extract_verbosity_from_options(options)

    # Assert
    assert result is not None
    assert result["verbosity"] == "high"


@pytest.mark.ai
def test_extract_verbosity__handles_dict__correctly() -> None:
    """
    Purpose: Verify text config works with dict input (non-UI clients).
    Why this matters: Direct API calls pass text config as dict.
    Setup summary: Pass text as dict, verify it's returned correctly.
    """
    # Arrange
    options = {"text": {"verbosity": "medium"}}

    # Act
    result = extract_verbosity_from_options(options)

    # Assert
    assert result is not None
    assert result["verbosity"] == "medium"


@pytest.mark.ai
def test_extract_verbosity__handles_invalid_json__gracefully() -> None:
    """
    Purpose: Verify invalid JSON string doesn't crash, logs warning.
    Why this matters: Malformed input must not break the API pipeline.
    Setup summary: Pass invalid JSON, verify None returned (failsafe).
    """
    # Arrange
    options = {"text": '{"invalid": json}'}

    # Act
    result = extract_verbosity_from_options(options)

    # Assert
    # Function has @failsafe decorator, should return None for invalid input
    assert result is None


@pytest.mark.ai
def test_extract_verbosity__returns_none__when_missing() -> None:
    """
    Purpose: Verify function returns None when text not in options.
    Why this matters: Optional parameters must not cause errors.
    Setup summary: Pass options without text, verify None returned.
    """
    # Arrange
    options = {"temperature": 0.7}

    # Act
    result = extract_verbosity_from_options(options)

    # Assert
    assert result is None


@pytest.mark.ai
def test_extract_verbosity__uses_correct_variable_name() -> None:
    """
    Purpose: Verify variable name bug fix - uses text_config not reasoning.
    Why this matters: This was a bug in the original code that was fixed.
    Setup summary: Pass text config, verify it's processed with correct variable.
    """
    # Arrange
    options = {"text": {"verbosity": "low"}}

    # Act
    result = extract_verbosity_from_options(options)

    # Assert
    # This test ensures the variable name bug is fixed
    assert result is not None
    assert result["verbosity"] == "low"


# ============================================================================
# Tests for _responses_stream_with_rate_limit_retry
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_rate_limit_retry__succeeds_on_first_attempt() -> None:
    """
    Purpose: Verify that a successful call passes the result through without retrying.
    Why this matters: Happy path must not be affected by the retry wrapper.
    """
    expected = {"id": "resp_123"}
    mock_fn = AsyncMock(return_value=expected)

    with patch(
        "unique_toolkit.chat.responses_api.unique_sdk.Integrated.responses_stream_async",
        mock_fn,
    ):
        result = await _responses_stream_with_rate_limit_retry(
            responses_args={}, model_name="gpt-4o"
        )

    assert result == expected
    assert mock_fn.call_count == 1


@pytest.mark.asyncio
@pytest.mark.ai
async def test_rate_limit_retry__retries_on_rate_limit_error_and_succeeds() -> None:
    """
    Purpose: Verify the helper retries after a 429/rate-limit APIError and returns on success.
    Why this matters: Core behaviour - rate-limit errors should trigger backoff + retry.
    """
    expected = {"id": "resp_ok"}
    rate_limit_error = unique_sdk.APIError(
        "Internal server error\n(Original error) too_many_requests: Too Many Requests"
    )

    mock_fn = AsyncMock(side_effect=[rate_limit_error, expected])

    with (
        patch(
            "unique_toolkit.chat.responses_api.unique_sdk.Integrated.responses_stream_async",
            mock_fn,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        result = await _responses_stream_with_rate_limit_retry(
            responses_args={}, model_name="gpt-4o"
        )

    assert result == expected
    assert mock_fn.call_count == 2
    assert mock_sleep.call_count == 1


@pytest.mark.asyncio
@pytest.mark.ai
async def test_rate_limit_retry__uses_exponential_backoff() -> None:
    """
    Purpose: Verify exponential backoff is used (not a fixed delay).
    Why this matters: Retry-After is unavailable (SDK strips headers); backoff must scale.
    Note: The SDK wraps errors via `raise error_class(f"Failed after N attempts: {e}")`,
    discarding original HTTP headers, so Retry-After can never be read here.
    """
    expected = {"id": "resp_ok"}
    error = unique_sdk.APIError(
        "Internal server error\n(Original error) too_many_requests: Too Many Requests"
    )

    mock_fn = AsyncMock(side_effect=[error, expected])

    with (
        patch(
            "unique_toolkit.chat.responses_api.unique_sdk.Integrated.responses_stream_async",
            mock_fn,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await _responses_stream_with_rate_limit_retry(
            responses_args={}, model_name="gpt-4o"
        )

    assert mock_sleep.call_count == 1
    # First retry: 30s base + up to 10% jitter -> between 30s and 33s
    actual_wait = mock_sleep.call_args[0][0]
    assert 30.0 <= actual_wait <= 33.0


@pytest.mark.asyncio
@pytest.mark.ai
async def test_rate_limit_retry__raises_after_max_attempts() -> None:
    """
    Purpose: Verify that the error is re-raised after all retry attempts are exhausted.
    Why this matters: We must not loop forever; ultimately the caller needs to handle the error.
    """
    rate_limit_error = unique_sdk.APIError(
        "Internal server error\n(Original error) too_many_requests: Too Many Requests"
    )

    mock_fn = AsyncMock(side_effect=rate_limit_error)

    with (
        patch(
            "unique_toolkit.chat.responses_api.unique_sdk.Integrated.responses_stream_async",
            mock_fn,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(unique_sdk.APIError),
    ):
        await _responses_stream_with_rate_limit_retry(
            responses_args={}, model_name="gpt-4o"
        )

    assert mock_fn.call_count == rate_limit_retry_config.max_attempts


@pytest.mark.asyncio
@pytest.mark.ai
async def test_rate_limit_retry__does_not_retry_non_rate_limit_errors() -> None:
    """
    Purpose: Verify that non-rate-limit errors are re-raised immediately without retrying.
    Why this matters: Only 429s should trigger backoff; other errors should fail fast.
    """
    other_error = unique_sdk.APIError(
        "Internal server error\n(Original error) context_length_exceeded"
    )

    mock_fn = AsyncMock(side_effect=other_error)

    with (
        patch(
            "unique_toolkit.chat.responses_api.unique_sdk.Integrated.responses_stream_async",
            mock_fn,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        pytest.raises(unique_sdk.APIError),
    ):
        await _responses_stream_with_rate_limit_retry(
            responses_args={}, model_name="gpt-4o"
        )

    assert mock_fn.call_count == 1
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.ai
async def test_rate_limit_retry__invokes_callback_before_each_retry_sleep() -> None:
    """
    Purpose: Verify on_rate_limit_retry callback is called with (attempt_1based, wait_secs).
    Why this matters: Message-log integration relies on this; same contract as before_sleep.
    """
    expected = {"id": "resp_ok"}
    rate_limit_error = unique_sdk.APIError(
        "Internal server error\n(Original error) too_many_requests: Too Many Requests"
    )
    mock_fn = AsyncMock(side_effect=[rate_limit_error, expected])
    callback_calls: list[tuple[int, float]] = []

    async def on_retry(attempt: int, wait_secs: float) -> None:
        callback_calls.append((attempt, wait_secs))

    with (
        patch(
            "unique_toolkit.chat.responses_api.unique_sdk.Integrated.responses_stream_async",
            mock_fn,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await _responses_stream_with_rate_limit_retry(
            responses_args={},
            model_name="gpt-4o",
            on_rate_limit_retry=on_retry,
        )

    assert result == expected
    assert len(callback_calls) == 1
    assert callback_calls[0][0] == 1  # first retry = attempt 1
    assert 30.0 <= callback_calls[0][1] <= 33.0  # first wait 30s + up to 10% jitter


# ============================================================================
# Tests for convert_messages_to_openai
# ============================================================================


@pytest.mark.ai
def test_convert_messages__returns_string_as_is() -> None:
    """
    Purpose: Verify that a plain string input is returned unchanged.
    Why this matters: The Responses API accepts a raw string as input.
    Setup summary: Pass a string, verify it's returned as-is.
    """
    result = convert_messages_to_openai("Hello, world!")
    assert result == "Hello, world!"


@pytest.mark.ai
def test_convert_messages__converts_language_model_messages() -> None:
    """
    Purpose: Verify that LanguageModelMessages are converted to OpenAI format.
    Why this matters: Internal message types must be serialized for the OpenAI API.
    Setup summary: Pass LanguageModelMessages, verify a list of dicts is returned.
    """
    messages = LanguageModelMessages(
        [
            LanguageModelSystemMessage(content="You are helpful."),
            LanguageModelUserMessage(content="Hi"),
        ]
    )
    result = convert_messages_to_openai(messages)
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.ai
def test_convert_messages__converts_sequence_of_message_objects() -> None:
    """
    Purpose: Verify that a sequence of LanguageModelMessageOptions is converted.
    Why this matters: Callers may pass a plain list of message objects rather than LanguageModelMessages.
    Setup summary: Pass a list of message objects, verify conversion to list.
    """
    messages = [
        LanguageModelUserMessage(content="What's the weather?"),
    ]
    result = convert_messages_to_openai(messages)
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.ai
def test_convert_messages__passes_through_openai_dicts() -> None:
    """
    Purpose: Verify that already-formatted OpenAI dicts are passed through.
    Why this matters: Callers may mix native OpenAI params with toolkit messages.
    Setup summary: Pass a list of dicts, verify they appear in the output.
    """
    messages = [{"role": "user", "content": "Hello"}]
    result = convert_messages_to_openai(messages)
    assert isinstance(result, list)
    assert result[0] == {"role": "user", "content": "Hello"}


# ============================================================================
# Tests for _prepare_responses_params_util
# ============================================================================


@pytest.mark.ai
@pytest.mark.parametrize(
    "model_name",
    list(LanguageModelName),
    ids=[model_name.name for model_name in LanguageModelName],
)
def test_prepare_responses_params__sends_enum_value_not_member_name(
    model_name: LanguageModelName,
) -> None:
    """
    Purpose: Verify the outgoing model identifier is the enum value, never the member name.
    Why this matters: LiteLLM members have a member name (LITELLM_OPENAI_GPT_56_LUNA) that
    differs from their value (litellm:openai-gpt-5-6-luna). Sending the member name made the
    backend reject the request as not available on the cluster (UN-24591). Azure members have
    name == value, which is why this stayed invisible until a LiteLLM model was used.
    Setup summary: Prepare params for every known model, assert the value form is emitted.
    """
    params = _prepare_responses_params_util(
        model_name=model_name,
        content_chunks=None,
        temperature=0.0,
        tools=None,
        messages="Hello",
        reasoning=None,
        text=None,
    )

    assert params.model_name == model_name.value


@pytest.mark.ai
def test_prepare_responses_params__passes_custom_model_string_through() -> None:
    """
    Purpose: Verify a plain string model name is forwarded unchanged.
    Why this matters: Custom models are not enum members and must not be rewritten.
    Setup summary: Pass a custom model string, assert it survives verbatim.
    """
    params = _prepare_responses_params_util(
        model_name="litellm:customer-private-model",
        content_chunks=None,
        temperature=0.0,
        tools=None,
        messages="Hello",
        reasoning=None,
        text=None,
    )

    assert params.model_name == "litellm:customer-private-model"


# ============================================================================
# Tests for chat-completions option translation on the Responses path
# ============================================================================


def _build_openai_options(other_options: dict) -> dict:
    """Run the full prepare pipeline and return the ``options`` forwarded to OpenAI."""
    params = _prepare_responses_params_util(
        model_name=LanguageModelName.AZURE_GPT_55_2026_0424,
        content_chunks=None,
        temperature=1.0,
        tools=None,
        messages="Hello",
        reasoning=None,
        text=None,
        other_options=other_options,
    )
    args = _prepare_responses_args(
        company_id="company",
        user_id="user",
        assistant_message_id="am",
        user_message_id="um",
        chat_id="chat",
        assistant_id="assistant",
        params=params,
        debug_info=None,
        start_text=None,
        include=None,
        instructions=None,
        max_output_tokens=None,
        metadata=None,
        parallel_tool_calls=None,
        tool_choice=None,
        top_p=None,
        other_options=other_options,
    )
    return args["options"]


@pytest.mark.ai
def test_strip_translated_options__removes_reasoning_and_verbosity_keys() -> None:
    """
    Purpose: Verify every spelling that is translated into ``reasoning``/``text`` is dropped.
    Why this matters: /v1/responses rejects flat ``verbosity`` / ``reasoning_effort`` with
      "Unrecognized request argument" (UN-20123); anything else must pass through untouched.
    Setup summary: Strip a dict mixing translated keys and an unrelated key.
    """
    result = strip_translated_responses_options(
        {
            "reasoning": {"effort": "low"},
            "reasoning_effort": "low",
            "reasoningEffort": "low",
            "verbosity": "low",
            "text": {"verbosity": "low"},
            "user": "space-1",
        }
    )

    assert result == {"user": "space-1"}
    assert strip_translated_responses_options(None) == {}


@pytest.mark.ai
def test_prepare_responses_args__maps_flat_verbosity_to_text_and_drops_flat_key() -> (
    None
):
    """
    Purpose: ``verbosity`` from additional_llm_options reaches OpenAI only as ``text.verbosity``.
    Why this matters: GPT-5.5 spaces configured with ``verbosity`` (chat-completions style)
      failed with 400 once routed through the Responses API because the flat key leaked
      into the request next to the translated ``text`` config.
    Setup summary: Prepare args with ``verbosity: low``; assert ``text`` set, ``verbosity`` absent.
    """
    options = _build_openai_options({"verbosity": "low"})

    assert options["text"] == {"verbosity": "low"}
    assert "verbosity" not in options


@pytest.mark.ai
@pytest.mark.parametrize("key", ["reasoning_effort", "reasoningEffort"])
def test_prepare_responses_args__maps_flat_reasoning_effort_and_drops_flat_key(
    key: str,
) -> None:
    """
    Purpose: Flat ``reasoning_effort`` / ``reasoningEffort`` reach OpenAI only as
      ``reasoning.effort``.
    Why this matters: Same 400 as for ``verbosity``; both spellings are accepted in
      space configs and must be normalised identically.
    Setup summary: Prepare args with the flat key; assert nested effort set, flat key absent.
    """
    options = _build_openai_options({key: "high"})

    assert options["reasoning"]["effort"] == "high"
    assert "reasoning_effort" not in options
    assert "reasoningEffort" not in options


@pytest.mark.ai
def test_prepare_responses_args__keeps_unrelated_other_options() -> None:
    """
    Purpose: Only translated keys are stripped; genuine Responses options still pass through.
    Why this matters: ``other_options`` is the escape hatch for arbitrary create() kwargs.
    Setup summary: Prepare args with a translated key plus ``user``; assert ``user`` survives.
    """
    options = _build_openai_options({"verbosity": "low", "user": "space-1"})

    assert options["user"] == "space-1"
    assert options["text"] == {"verbosity": "low"}
