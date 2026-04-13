"""Tests for the content-filter error handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import unique_sdk

from unique_toolkit.agentic.loop_runner._refusal_handler import (
    CONTENT_FILTER_MESSAGE,
    is_content_filter_error,
    make_content_filter_response,
)

# ---------------------------------------------------------------------------
# is_content_filter_error
# ---------------------------------------------------------------------------


def _unique_error(
    code: str | None = None, message: str = "error"
) -> unique_sdk.UniqueError:
    err = unique_sdk.UniqueError(message=message, http_status=400, code=code)
    return err


class TestIsContentFilterError:
    def test_unique_sdk_error_with_content_filter_code(self):
        assert is_content_filter_error(_unique_error(code="content_filter")) is True

    def test_unique_sdk_error_with_content_filter_in_message(self):
        assert (
            is_content_filter_error(_unique_error(message="content_filter triggered"))
            is True
        )

    def test_unique_sdk_error_with_responsibleai_in_message(self):
        assert (
            is_content_filter_error(
                _unique_error(message="ResponsibleAI policy violation")
            )
            is True
        )

    def test_unique_sdk_error_unrelated_code(self):
        assert (
            is_content_filter_error(
                _unique_error(code="rate_limit", message="too many requests")
            )
            is False
        )

    def test_generic_exception_returns_false(self):
        assert is_content_filter_error(ValueError("something went wrong")) is False

    def test_runtime_error_returns_false(self):
        assert is_content_filter_error(RuntimeError("unexpected")) is False

    def test_openai_bad_request_with_content_filter_code(self):
        try:
            import httpx
            from openai import BadRequestError

            response = httpx.Response(
                400, request=httpx.Request("POST", "https://api.openai.com")
            )
            exc = BadRequestError(
                message="content filter triggered",
                response=response,
                body={"code": "content_filter"},
            )
            assert is_content_filter_error(exc) is True
        except ImportError:
            pytest.skip("openai not installed")

    def test_openai_bad_request_without_content_filter_code(self):
        try:
            import httpx
            from openai import BadRequestError

            response = httpx.Response(
                400, request=httpx.Request("POST", "https://api.openai.com")
            )
            exc = BadRequestError(
                message="invalid request",
                response=response,
                body={"code": "invalid_request_error"},
            )
            assert is_content_filter_error(exc) is False
        except ImportError:
            pytest.skip("openai not installed")


# ---------------------------------------------------------------------------
# make_content_filter_response
# ---------------------------------------------------------------------------


class TestMakeContentFilterResponse:
    def test_returns_response_with_friendly_message(self):
        response = make_content_filter_response()
        assert response.message.text == CONTENT_FILTER_MESSAGE
        assert "flagged" in (response.message.text or "")
        assert "rephrase" in (response.message.text or "").lower()

    def test_no_tool_calls(self):
        response = make_content_filter_response()
        assert response.tool_calls is None

    def test_empty_output(self):
        response = make_content_filter_response()
        assert response.output == []

    def test_is_not_empty(self):
        """Orchestrator must not treat this as an empty response."""
        response = make_content_filter_response()
        assert response.message.text  # truthy — has content


# ---------------------------------------------------------------------------
# Integration: iteration handlers surface friendly message on content filter
# ---------------------------------------------------------------------------


def _make_mock_response():
    from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
    from unique_toolkit.language_model.schemas import (
        ResponsesLanguageModelStreamResponse,
    )

    message = ChatMessage(
        id="msg_ok",
        chat_id="chat_1",
        role=ChatMessageRole.ASSISTANT,
        text="Here is your analysis.",
        original_text="Here is your analysis.",
        references=[],
    )
    return ResponsesLanguageModelStreamResponse(
        message=message, tool_calls=None, output=[]
    )


@pytest.mark.asyncio
async def test_handle_responses_normal_iteration_content_filter():
    from unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils import (
        handle_responses_normal_iteration,
    )

    content_filter_exc = _unique_error(code="content_filter")

    with patch(
        "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
        new=AsyncMock(side_effect=content_filter_exc),
    ):
        result = await handle_responses_normal_iteration(
            iteration_index=0,
            model_name="gpt-4o",
            instructions=None,
            messages=[],
            tools=None,
            tool_choice=None,
            tool_choices=None,
            other_options={},
            event=None,  # type: ignore[arg-type]
            on_rate_limit_retry=None,
        )

    assert result.message.text == CONTENT_FILTER_MESSAGE
    assert result.tool_calls is None


@pytest.mark.asyncio
async def test_handle_responses_normal_iteration_reraises_unrelated_error():
    from unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils import (
        handle_responses_normal_iteration,
    )

    unrelated_exc = RuntimeError("something totally different")

    with patch(
        "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
        new=AsyncMock(side_effect=unrelated_exc),
    ):
        with pytest.raises(RuntimeError, match="something totally different"):
            await handle_responses_normal_iteration(
                iteration_index=0,
                model_name="gpt-4o",
                instructions=None,
                messages=[],
                tools=None,
                tool_choice=None,
                tool_choices=None,
                other_options={},
                event=None,  # type: ignore[arg-type]
                on_rate_limit_retry=None,
            )


@pytest.mark.asyncio
async def test_handle_responses_last_iteration_content_filter():
    from unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils import (
        handle_responses_last_iteration,
    )

    content_filter_exc = _unique_error(code="content_filter")

    with patch(
        "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
        new=AsyncMock(side_effect=content_filter_exc),
    ):
        result = await handle_responses_last_iteration(
            iteration_index=0,
            model_name="gpt-4o",
            instructions=None,
            messages=[],
            tools=None,
            tool_choice=None,
            tool_choices=None,
            other_options={},
            event=None,  # type: ignore[arg-type]
            on_rate_limit_retry=None,
        )

    assert result.message.text == CONTENT_FILTER_MESSAGE


@pytest.mark.asyncio
async def test_handle_responses_normal_iteration_passes_through_on_success():
    from unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils import (
        handle_responses_normal_iteration,
    )

    ok_response = _make_mock_response()

    with patch(
        "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
        new=AsyncMock(return_value=ok_response),
    ):
        result = await handle_responses_normal_iteration(
            iteration_index=0,
            model_name="gpt-4o",
            instructions=None,
            messages=[],
            tools=None,
            tool_choice=None,
            tool_choices=None,
            other_options={},
            event=None,  # type: ignore[arg-type]
            on_rate_limit_retry=None,
        )

    assert result.message.text == "Here is your analysis."
