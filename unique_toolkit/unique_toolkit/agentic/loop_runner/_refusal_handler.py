"""Utilities for handling platform-level content-filter blocks.

When Azure's content-safety filter rejects a request it raises an HTTP 400
error with ``code="content_filter"`` *before* the model ever responds.  We
catch that exception in the iteration handlers and surface a clear,
actionable message to the user instead of letting a raw API error propagate.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import unique_sdk

if TYPE_CHECKING:
    from unique_toolkit.language_model.schemas import (
        ResponsesLanguageModelStreamResponse,
    )

_LOGGER = logging.getLogger(__name__)

# Shown to the user when Azure's content-safety filter blocks a request.
CONTENT_FILTER_MESSAGE = (
    "Your request was flagged by the platform's safety system and couldn't be processed. "
    "This sometimes happens with financial terminology.\n\n"
    "A few things that usually help:\n"
    "- **Rephrase or break the request into smaller steps**\n"
    "- **Try again** — transient flags occasionally clear on retry\n"
    "- If it keeps happening, let your administrator know so they can adjust the content filter settings"
)

# Azure sets code="content_filter" on the 400 error body.
_CONTENT_FILTER_CODES = ("content_filter",)
_CONTENT_FILTER_MESSAGE_FRAGMENTS = (
    "content filter",
    "content_filter",
    "ResponsibleAI",
)


def is_content_filter_error(exc: BaseException) -> bool:
    """Return ``True`` when *exc* is an Azure content-filter block.

    Checks:
    1. OpenAI SDK's typed ``ContentFilterFinishReasonError`` / ``BadRequestError``
       with ``code="content_filter"``.
    2. ``unique_sdk.UniqueError`` with ``code="content_filter"``.
    3. String-pattern fallback on the exception message.
    """
    try:
        from openai import BadRequestError, ContentFilterFinishReasonError

        if isinstance(exc, ContentFilterFinishReasonError):
            _LOGGER.warning("ContentFilterFinishReasonError detected")
            return True

        if (
            isinstance(exc, BadRequestError)
            and getattr(exc, "code", None) in _CONTENT_FILTER_CODES
        ):
            _LOGGER.warning("OpenAI BadRequestError with content_filter code detected")
            return True
    except ImportError:
        pass

    if isinstance(exc, unique_sdk.UniqueError):
        if getattr(exc, "code", None) in _CONTENT_FILTER_CODES:
            _LOGGER.warning(
                "Content filter block detected via unique_sdk error code: %s",
                exc.code,
            )
            return True

        msg = str(exc).lower()
        if any(
            fragment.lower() in msg for fragment in _CONTENT_FILTER_MESSAGE_FRAGMENTS
        ):
            _LOGGER.warning(
                "Content filter block detected via message fragment: %s",
                str(exc)[:200],
            )
            return True

    return False


def make_content_filter_response() -> ResponsesLanguageModelStreamResponse:
    """Build a synthetic response carrying the content-filter user message.

    The orchestrator treats this like a normal final response (no tool calls,
    text present) and writes the text back to the assistant message.
    """
    from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
    from unique_toolkit.language_model.schemas import (
        ResponsesLanguageModelStreamResponse,
    )

    message = ChatMessage(
        id="content_filter_error",
        chat_id="",
        role=ChatMessageRole.ASSISTANT,
        text=CONTENT_FILTER_MESSAGE,
        original_text=CONTENT_FILTER_MESSAGE,
        references=[],
    )
    return ResponsesLanguageModelStreamResponse(
        message=message,
        tool_calls=None,
        output=[],
    )
