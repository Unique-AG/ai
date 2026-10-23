from collections import OrderedDict
from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.chat.functions import (
    stream_complete_with_references,
    stream_complete_with_references_async,
)
from unique_toolkit.chat.responses_api import (
    stream_responses_with_references,
    stream_responses_with_references_async,
)
from unique_toolkit.language_model import LanguageModelCallError
from unique_toolkit.language_model.errors import (
    _language_model_call_error_from,
    _reraise_as_language_model_call_error,
)
from unique_toolkit.language_model.functions import complete, complete_async
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import LanguageModelMessages

pytestmark = pytest.mark.ai

_FILTER_MESSAGE = (
    "The response was filtered due to the prompt triggering the content "
    "filter management policy of the AI model. Please modify your prompt and retry."
)
_MODEL = LanguageModelName.AZURE_GPT_4_0613


def _content_filter_error() -> unique_sdk.InvalidRequestError:
    return unique_sdk.InvalidRequestError(
        _FILTER_MESSAGE,
        params=OrderedDict(
            [
                ("retryable", False),
                ("correlationId", "corr-1"),
                ("model", "gpt-4o-2024-11-20"),
            ]
        ),
        code="content_filter",
        http_status=400,
        original_error="<Unknown code>: <No message>",
    )


def _assert_content_filter(
    raised: BaseException,
    source: unique_sdk.InvalidRequestError,
) -> None:
    assert isinstance(raised, LanguageModelCallError)
    assert isinstance(raised, unique_sdk.APIError)
    assert raised.code == "content_filter"
    assert raised.user_message == _FILTER_MESSAGE
    assert raised.retryable is False
    assert raised.correlation_id == "corr-1"
    assert raised.http_status == 400
    assert str(raised) == _FILTER_MESSAGE
    assert "(Original error)" not in str(raised)


def test_language_model_call_error_from__converts_content_filter__contract_shape() -> (
    None
):
    """Purpose: Verify a content-filter SDK error becomes LanguageModelCallError.
    Why this matters: Assistants must display the API sentence, not the SDK suffix.
    Setup summary: Convert an InvalidRequestError shaped like the live node-chat body.
    """
    source = _content_filter_error()

    converted = _language_model_call_error_from(source)

    assert converted is not None
    _assert_content_filter(converted, source)
    assert converted.__cause__ is None


def test_language_model_call_error_from__drops_non_string_correlation_id() -> None:
    """Purpose: Verify a non-string correlation id is stored as None.
    Why this matters: Callers append the id to unknown-code messages and need a str.
    Setup summary: Convert a contract error whose correlationId is a number.
    """
    source = unique_sdk.InvalidRequestError(
        _FILTER_MESSAGE,
        params={"retryable": True, "correlationId": 12},
        code="rate_limit",
        http_status=429,
    )

    converted = _language_model_call_error_from(source)

    assert converted is not None
    assert converted.correlation_id is None
    assert converted.retryable is True
    assert converted.code == "rate_limit"


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(
            unique_sdk.APIError("upstream failed", http_status=500),
            id="legacy-api-error",
        ),
        pytest.param(
            unique_sdk.InvalidRequestError(
                "bad id",
                params="id",
                code="invalid_request",
                http_status=400,
            ),
            id="string-params",
        ),
        pytest.param(
            unique_sdk.InvalidRequestError(
                _FILTER_MESSAGE,
                params={"model": "gpt-4o"},
                code="content_filter",
                http_status=400,
            ),
            id="retryable-missing",
        ),
        pytest.param(
            unique_sdk.InvalidRequestError(
                _FILTER_MESSAGE,
                params={"retryable": "false"},
                code="content_filter",
                http_status=400,
            ),
            id="retryable-not-bool",
        ),
        pytest.param(
            unique_sdk.InvalidRequestError(
                "",
                params={"retryable": False},
                code="content_filter",
                http_status=400,
            ),
            id="empty-message",
        ),
        pytest.param(
            unique_sdk.InvalidRequestError(
                _FILTER_MESSAGE,
                params={"retryable": False},
                code="",
                http_status=400,
            ),
            id="empty-code",
        ),
        pytest.param(
            LanguageModelCallError(
                code="content_filter",
                user_message=_FILTER_MESSAGE,
                retryable=False,
                correlation_id="corr-1",
                http_status=400,
            ),
            id="already-converted",
        ),
    ],
)
def test_language_model_call_error_from__returns_none__outside_contract(
    error: unique_sdk.UniqueError,
) -> None:
    """Purpose: Verify legacy and incomplete SDK errors are not converted.
    Why this matters: Wrapping those would hide the original type from existing callers.
    Setup summary: Pass errors that miss code, retryable, or a user message.
    """
    assert _language_model_call_error_from(error) is None


def test_reraise_as_language_model_call_error__keeps_converted_error() -> None:
    """Purpose: Verify an already converted error is re-raised as the same object.
    Why this matters: Nested toolkit calls must not convert its cause a second time.
    Setup summary: Re-raise a LanguageModelCallError whose cause is a contract error.
    """
    converted = _language_model_call_error_from(_content_filter_error())
    assert converted is not None
    converted.__cause__ = _content_filter_error()

    with pytest.raises(LanguageModelCallError) as caught:
        _reraise_as_language_model_call_error(converted)

    assert caught.value is converted


@patch.object(unique_sdk.ChatCompletion, "create")
def test_complete__raises_language_model_call_error__content_filter(
    mock_create,
) -> None:
    """Purpose: Verify sync completion surfaces the content-filter contract.
    Why this matters: Keyword extraction and other sync callers share this path.
    Setup summary: Make ChatCompletion.create raise the live content-filter error.
    """
    source = _content_filter_error()
    mock_create.side_effect = source

    with pytest.raises(LanguageModelCallError) as caught:
        complete(
            company_id="company",
            user_id="user",
            messages=LanguageModelMessages([]),
            model_name=_MODEL,
        )

    _assert_content_filter(caught.value, source)
    assert caught.value.__cause__ is source


@pytest.mark.asyncio
@patch.object(unique_sdk.ChatCompletion, "create_async")
async def test_complete_async__raises_language_model_call_error__content_filter(
    mock_create,
) -> None:
    """Purpose: Verify async completion surfaces the content-filter contract.
    Why this matters: Document Search keyword extraction calls complete_async.
    Setup summary: Make ChatCompletion.create_async raise the live content-filter error.
    """
    source = _content_filter_error()
    mock_create.side_effect = source

    with pytest.raises(LanguageModelCallError) as caught:
        await complete_async(
            company_id="company",
            user_id="user",
            messages=LanguageModelMessages([]),
            model_name=_MODEL,
        )

    _assert_content_filter(caught.value, source)
    assert caught.value.__cause__ is source


@pytest.mark.asyncio
@patch.object(unique_sdk.ChatCompletion, "create_async")
async def test_complete_async__reraises_original__legacy_api_error(
    mock_create,
) -> None:
    """Purpose: Verify a legacy API error keeps its type and identity.
    Why this matters: 5xx errors do not carry the contract until the SDK ticket lands.
    Setup summary: Make create_async raise an APIError with no code or params.
    """
    source = unique_sdk.APIError("upstream failed", http_status=500)
    mock_create.side_effect = source

    with pytest.raises(unique_sdk.APIError) as caught:
        await complete_async(
            company_id="company",
            user_id="user",
            messages=LanguageModelMessages([]),
            model_name=_MODEL,
        )

    assert caught.value is source


@pytest.mark.asyncio
@patch.object(unique_sdk.ChatCompletion, "create_async")
async def test_complete_async__raises_language_model_call_error__after_sdk_retries(
    mock_create,
) -> None:
    """Purpose: Verify the contract is read from the error the SDK retried.
    Why this matters: After its last retry the SDK raises "Failed after N attempts".
    Setup summary: Raise that wrapper with a provider_unavailable 503 as its cause.
    """
    last_error = unique_sdk.APIError(
        "The model provider is unavailable. Please try again later.",
        params={"retryable": True, "correlationId": "corr-5"},
        code="provider_unavailable",
        http_status=503,
    )
    wrapper = unique_sdk.APIError(f"Failed after 3 attempts: {last_error}")
    wrapper.__cause__ = last_error
    mock_create.side_effect = wrapper

    with pytest.raises(LanguageModelCallError) as caught:
        await complete_async(
            company_id="company",
            user_id="user",
            messages=LanguageModelMessages([]),
            model_name=_MODEL,
        )

    assert caught.value.code == "provider_unavailable"
    assert (
        caught.value.user_message
        == "The model provider is unavailable. Please try again later."
    )
    assert caught.value.http_status == 503
    assert caught.value.__cause__ is wrapper


@pytest.mark.asyncio
@patch.object(unique_sdk.ChatCompletion, "create_async")
async def test_complete_async__reraises_original__unrelated_exception(
    mock_create,
) -> None:
    """Purpose: Verify non-SDK failures are not wrapped.
    Why this matters: Programming errors must not look like model-call failures.
    Setup summary: Make create_async raise a RuntimeError.
    """
    source = RuntimeError("boom")
    mock_create.side_effect = source

    with pytest.raises(RuntimeError) as caught:
        await complete_async(
            company_id="company",
            user_id="user",
            messages=LanguageModelMessages([]),
            model_name=_MODEL,
        )

    assert caught.value is source


_STREAM_ARGS = {
    "company_id": "company",
    "user_id": "user",
    "assistant_message_id": "assistant-message",
    "user_message_id": "user-message",
    "chat_id": "chat",
    "assistant_id": "assistant",
    "messages": LanguageModelMessages([]),
    "model_name": _MODEL,
}


@patch.object(unique_sdk.Integrated, "chat_stream_completion")
def test_stream_complete_with_references__raises_language_model_call_error__content_filter(
    mock_stream,
) -> None:
    """Purpose: Verify sync answer streaming surfaces the content-filter contract.
    Why this matters: The sync stream is the twin of the call Document Search uses.
    Setup summary: Make chat_stream_completion raise the live content-filter error.
    """
    source = _content_filter_error()
    mock_stream.side_effect = source

    with pytest.raises(LanguageModelCallError) as caught:
        stream_complete_with_references(**_STREAM_ARGS)

    _assert_content_filter(caught.value, source)
    assert caught.value.__cause__ is source


@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
async def test_stream_complete_with_references_async__raises_language_model_call_error__content_filter(
    mock_stream,
) -> None:
    """Purpose: Verify async answer streaming surfaces the content-filter contract.
    Why this matters: This is the call that showed the capacity sentence on cat-prod.
    Setup summary: Make chat_stream_completion_async raise the live content-filter error.
    """
    source = _content_filter_error()
    mock_stream.side_effect = source

    with pytest.raises(LanguageModelCallError) as caught:
        await stream_complete_with_references_async(**_STREAM_ARGS)

    _assert_content_filter(caught.value, source)
    assert caught.value.__cause__ is source


_RESPONSES_ARGS = {
    "company_id": "company",
    "user_id": "user",
    "assistant_message_id": "assistant-message",
    "user_message_id": "user-message",
    "chat_id": "chat",
    "assistant_id": "assistant",
    "messages": "hello",
    "model_name": _MODEL,
}


@patch.object(unique_sdk.Integrated, "responses_stream")
def test_stream_responses_with_references__raises_language_model_call_error__content_filter(
    mock_stream,
) -> None:
    """Purpose: Verify sync Responses streaming surfaces the content-filter contract.
    Why this matters: Unique AI's sync twin must show the same sentence as chat completions.
    Setup summary: Make responses_stream raise the live content-filter error.
    """
    source = _content_filter_error()
    mock_stream.side_effect = source

    with pytest.raises(LanguageModelCallError) as caught:
        stream_responses_with_references(**_RESPONSES_ARGS)

    _assert_content_filter(caught.value, source)
    assert caught.value.__cause__ is source


@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "responses_stream_async")
async def test_stream_responses_with_references_async__raises_language_model_call_error__content_filter(
    mock_stream,
) -> None:
    """Purpose: Verify async Responses streaming surfaces the content-filter contract.
    Why this matters: Unique AI reports model failures from this call.
    Setup summary: Make responses_stream_async raise the live content-filter error.
    """
    source = _content_filter_error()
    mock_stream.side_effect = source

    with pytest.raises(LanguageModelCallError) as caught:
        await stream_responses_with_references_async(**_RESPONSES_ARGS)

    _assert_content_filter(caught.value, source)
    assert caught.value.__cause__ is source


@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "responses_stream_async")
async def test_stream_responses_with_references_async__reraises_original__legacy_api_error(
    mock_stream,
) -> None:
    """Purpose: Verify a non-contract Responses error is not converted after retry.
    Why this matters: Rate-limit retry must still see the original APIError.
    Setup summary: Make responses_stream_async raise an APIError with no contract fields.
    """
    source = unique_sdk.APIError("upstream failed", http_status=500)
    mock_stream.side_effect = source

    with pytest.raises(unique_sdk.APIError) as caught:
        await stream_responses_with_references_async(**_RESPONSES_ARGS)

    assert caught.value is source


@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "responses_stream_async")
async def test_stream_responses_with_references_async__retries_retryable_rate_limit(
    mock_stream,
) -> None:
    """Purpose: Verify a retryable RateLimitError is tried again after the API wait.
    Why this matters: The SDK no longer retries 429s, so this layer owns that wait.
    Setup summary: Fail once with retryAfterSeconds 0, then return a stream result.
    """
    mock_stream.side_effect = [
        unique_sdk.RateLimitError(
            "The model is receiving too many requests. Please retry.",
            params={
                "retryable": True,
                "retryAfterSeconds": 0,
                "correlationId": "corr-9",
            },
            code="rate_limited",
            http_status=429,
        ),
        {
            "id": "resp-1",
            "message": {
                "id": "msg-1",
                "chatId": "chat-1",
                "role": "assistant",
                "text": "ok",
            },
            "toolCalls": [],
            "output": [],
        },
    ]

    result = await stream_responses_with_references_async(**_RESPONSES_ARGS)

    assert result.message.text == "ok"
    assert mock_stream.call_count == 2
