"""
Unit tests for SubAgentTool's assessment forwarding when passthrough is enabled.

These tests bypass the SubAgentTool constructor (which requires a full ChatEvent
and ChatService) and exercise the assessment-forwarding helpers in isolation.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.tools.a2a.tool.config import (
    SubAgentPassthroughConfig,
    SubAgentToolConfig,
)
from unique_toolkit.agentic.tools.a2a.tool.service import SubAgentTool
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
)


def _make_ctx(tool: SubAgentTool) -> MagicMock:
    ctx = MagicMock()
    ctx.chat_service = tool._chat_service  # pyright: ignore[reportAttributeAccessIssue]
    return ctx


@pytest.fixture
def assessment_dict() -> dict[str, Any]:
    """A well-formed Space.Assessment-like dict with all required keys."""
    return {
        "id": "a-1",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
        "messageId": "m-1",
        "status": ChatMessageAssessmentStatus.DONE.value,
        "explanation": "Looks good",
        "label": ChatMessageAssessmentLabel.GREEN.value,
        "type": ChatMessageAssessmentType.HALLUCINATION.value,
        "title": "Hallucination check",
        "companyId": "c-1",
        "userId": "u-1",
        "isVisible": True,
        "createdBy": "u-1",
    }


@pytest.fixture
def passthrough_tool() -> SubAgentTool:
    """
    Build a SubAgentTool without invoking its real __init__.

    The real constructor needs a full ChatEvent and instantiates ChatService /
    MessageStepLogger; for the helpers under test we only need `_chat_service`
    (mocked) and `config`.
    """
    tool: SubAgentTool = SubAgentTool.__new__(SubAgentTool)
    tool.config = SubAgentToolConfig(  # type: ignore[attr-defined]
        passthrough_config=SubAgentPassthroughConfig(
            enabled=True, include_assessments=True
        ),
    )

    chat_service = MagicMock()
    chat_service._assistant_message_id = "assistant-msg-id"
    chat_service.create_message_assessment_async = AsyncMock()
    chat_service.modify_assistant_message_async = AsyncMock()
    tool._chat_service = chat_service
    return tool


@pytest.mark.ai
@pytest.mark.asyncio
async def test_forward_sub_agent_assessments__no_op__when_list_empty(
    passthrough_tool: SubAgentTool,
) -> None:
    """
    Purpose: Verify _forward_sub_agent_assessments returns immediately on empty input.
    Why this matters: An empty list is common (sub-agent ran no assessments); we must
        not issue an SDK call in that case — it would create a pointless network round trip.
    Setup summary: Call the helper with an empty list, assert no chat-service calls were made.
    """
    # Arrange
    chat_service = passthrough_tool._chat_service

    # Act
    await passthrough_tool._forward_sub_agent_assessments(
        _make_ctx(passthrough_tool), []
    )

    # Assert
    chat_service.create_message_assessment_async.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_forward_sub_agent_assessments__forwards_each_assessment__on_happy_path(
    passthrough_tool: SubAgentTool,
    assessment_dict: dict[str, Any],
) -> None:
    """
    Purpose: Verify each well-formed assessment results in one create_message_assessment_async call
        on the orchestrator's assistant message ID, with the SDK enum strings mapped to the
        typed Chat enums.
    Why this matters: Forwarding assessments is the whole point of the include_assessments flag;
        missing or mis-typed calls would silently drop quality signals from the sub-agent.
    Setup summary: Build two assessments (one GREEN, one RED), call the helper, then inspect
        the recorded kwargs of each create_message_assessment_async call.
    """
    # Arrange
    chat_service = passthrough_tool._chat_service
    red_assessment = {
        **assessment_dict,
        "id": "a-2",
        "label": ChatMessageAssessmentLabel.RED.value,
        "explanation": "Hallucination detected",
        "isVisible": False,
    }

    # Act
    await passthrough_tool._forward_sub_agent_assessments(
        _make_ctx(passthrough_tool),
        [assessment_dict, red_assessment],  # type: ignore[list-item]
    )

    # Assert
    assert chat_service.create_message_assessment_async.await_count == 2
    first_call_kwargs = chat_service.create_message_assessment_async.await_args_list[
        0
    ].kwargs
    assert first_call_kwargs["assistant_message_id"] == "assistant-msg-id"
    assert first_call_kwargs["status"] == ChatMessageAssessmentStatus.DONE
    assert first_call_kwargs["type"] == ChatMessageAssessmentType.HALLUCINATION
    assert first_call_kwargs["label"] == ChatMessageAssessmentLabel.GREEN
    assert first_call_kwargs["title"] == "Hallucination check"
    assert first_call_kwargs["explanation"] == "Looks good"
    assert first_call_kwargs["is_visible"] is True

    second_call_kwargs = chat_service.create_message_assessment_async.await_args_list[
        1
    ].kwargs
    assert second_call_kwargs["label"] == ChatMessageAssessmentLabel.RED
    assert second_call_kwargs["explanation"] == "Hallucination detected"
    assert second_call_kwargs["is_visible"] is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_forward_sub_agent_assessments__continues_other_assessments__when_one_has_bad_enum(
    passthrough_tool: SubAgentTool,
    assessment_dict: dict[str, Any],
) -> None:
    """
    Purpose: Verify a single assessment with an unrecognized enum value (here: an unknown
        `type` outside HALLUCINATION/COMPLIANCE) does not abort the batch — well-formed
        peers still get forwarded.
    Why this matters: Sub-agents may return assessment types the toolkit doesn't recognize.
        We don't want one bad apple to block the entire forwarding pass and lose every
        signal the orchestrator could have surfaced.
    Setup summary: Build two assessments — one valid, one with `type='UNKNOWN'` — call the
        helper, assert only the valid one resulted in a chat-service call.
    """
    # Arrange
    chat_service = passthrough_tool._chat_service
    bad_assessment = {
        **assessment_dict,
        "id": "a-bad",
        "type": "UNKNOWN_TYPE_NOT_IN_ENUM",
    }

    # Act
    await passthrough_tool._forward_sub_agent_assessments(
        _make_ctx(passthrough_tool),
        [bad_assessment, assessment_dict],  # type: ignore[list-item]
    )

    # Assert
    # Each task is executed via SafeTaskExecutor; the bad one is logged-and-swallowed,
    # so only the good assessment results in a successful chat-service call.
    assert chat_service.create_message_assessment_async.await_count == 1
    good_kwargs = chat_service.create_message_assessment_async.await_args.kwargs
    assert good_kwargs["type"] == ChatMessageAssessmentType.HALLUCINATION


@pytest.mark.ai
@pytest.mark.asyncio
async def test_display_sub_agent_response__skips_assessment_forwarding__when_flag_off(
    passthrough_tool: SubAgentTool,
    assessment_dict: dict[str, Any],
) -> None:
    """
    Purpose: Verify _display_sub_agent_response does not forward assessments when
        passthrough_config.include_assessments is False, even if the sub-agent returned them.
    Why this matters: include_assessments is the explicit opt-out; respecting it is required
        to avoid leaking sub-agent quality signals into the orchestrator output when the
        operator disabled that behavior.
    Setup summary: Flip include_assessments to False, run _display_sub_agent_response with a
        response carrying assessments, and assert no create_message_assessment_async calls.
    """
    # Arrange
    passthrough_tool.config = SubAgentToolConfig(  # type: ignore[attr-defined]
        passthrough_config=SubAgentPassthroughConfig(
            enabled=True, include_assessments=False
        ),
    )
    chat_service = passthrough_tool._chat_service
    response = {
        "text": "Sub agent answer",
        "originalText": "Sub agent answer",
        "references": None,
        "assessment": [assessment_dict],
    }

    # Act
    await passthrough_tool._display_sub_agent_response(
        _make_ctx(passthrough_tool),
        response,  # type: ignore[arg-type]
    )

    # Assert
    chat_service.modify_assistant_message_async.assert_awaited_once()
    chat_service.create_message_assessment_async.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_display_sub_agent_response__forwards_assessments__when_flag_on(
    passthrough_tool: SubAgentTool,
    assessment_dict: dict[str, Any],
) -> None:
    """
    Purpose: Verify _display_sub_agent_response calls modify_assistant_message_async first and
        then forwards the assessments when include_assessments is True.
    Why this matters: The streamed message and the forwarded assessments together make up the
        passthrough contract; both must happen on a happy-path response.
    Setup summary: Provide a response with one assessment and assert both chat-service methods
        were called.
    """
    # Arrange
    chat_service = passthrough_tool._chat_service
    response = {
        "text": "Streamed text",
        "originalText": "Streamed text",
        "references": None,
        "assessment": [assessment_dict],
    }

    # Act
    await passthrough_tool._display_sub_agent_response(
        _make_ctx(passthrough_tool),
        response,  # type: ignore[arg-type]
    )

    # Assert
    chat_service.modify_assistant_message_async.assert_awaited_once()
    chat_service.create_message_assessment_async.assert_awaited_once()
