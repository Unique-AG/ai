"""Tests for sub-agent questions and the pending list (UN-30320)."""

from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.api_resources._elicitation import Elicitation
from unique_sdk.utils.subagent_question import (
    SubagentQuestion,
    as_subagent_question,
    find_subagent_question_async,
)

pytestmark = pytest.mark.ai


def _elicitation(
    *, elicitation_id: str, chat_id: str, metadata: dict[str, str] | None
) -> dict[str, object]:
    return {
        "id": elicitation_id,
        "chatId": chat_id,
        "message": "Which region?",
        "status": "PENDING",
        "metadata": metadata,
    }


def _marks(*, message_id: str) -> dict[str, str]:
    return {
        "subAgentName": "Client Researcher",
        "subAgentChatId": "chat-child",
        "subAgentMessageId": message_id,
    }


@pytest.mark.parametrize("wrapped", [False, True])
def test_list_pending__array_or_wrapped_object__returns_the_same_list(
    wrapped: bool,
) -> None:
    items = [
        _elicitation(elicitation_id="e1", chat_id="chat-a", metadata=None),
        _elicitation(elicitation_id="e2", chat_id="chat-b", metadata=None),
    ]
    response: object = {"elicitations": items} if wrapped else items
    with patch.object(Elicitation, "_static_request", return_value=response):
        pending = Elicitation.list_pending("user-1", "company-1")

    assert [item["id"] for item in pending] == ["e1", "e2"]


def test_list_pending__chat_id_given__keeps_only_that_chat() -> None:
    items = [
        _elicitation(elicitation_id="e1", chat_id="chat-a", metadata=None),
        _elicitation(elicitation_id="e2", chat_id="chat-b", metadata=None),
    ]
    with patch.object(Elicitation, "_static_request", return_value=items):
        pending = Elicitation.list_pending("user-1", "company-1", chat_id="chat-b")

    assert [item["id"] for item in pending] == ["e2"]


def test_list_pending__unexpected_response__returns_empty_list() -> None:
    with patch.object(Elicitation, "_static_request", return_value="nope"):
        assert Elicitation.list_pending("user-1", "company-1") == []


def test_as_subagent_question__marked_elicitation__reads_the_marks() -> None:
    elicitation = _elicitation(
        elicitation_id="e1", chat_id="chat-parent", metadata=_marks(message_id="m1")
    )

    assert as_subagent_question(elicitation) == SubagentQuestion(
        elicitation_id="e1",
        message="Which region?",
        subagent_chat_id="chat-child",
        subagent_message_id="m1",
    )


@pytest.mark.parametrize(
    "metadata", [None, {}, {"subAgentChatId": "chat-child"}, {"subAgentMessageId": ""}]
)
def test_as_subagent_question__marks_missing__returns_none(
    metadata: dict[str, str] | None,
) -> None:
    elicitation = _elicitation(
        elicitation_id="e1", chat_id="chat-parent", metadata=metadata
    )

    assert as_subagent_question(elicitation) is None


async def test_find__several_pending__returns_the_one_of_this_subagent_turn() -> None:
    items = [
        _elicitation(elicitation_id="own", chat_id="chat-parent", metadata=None),
        _elicitation(
            elicitation_id="other",
            chat_id="chat-parent",
            metadata=_marks(message_id="m-other"),
        ),
        _elicitation(
            elicitation_id="mine",
            chat_id="chat-parent",
            metadata=_marks(message_id="m-mine"),
        ),
        _elicitation(
            elicitation_id="elsewhere",
            chat_id="chat-unrelated",
            metadata=_marks(message_id="m-mine"),
        ),
    ]
    with patch.object(
        Elicitation, "_static_request_async", new=AsyncMock(return_value=items)
    ):
        question = await find_subagent_question_async(
            user_id="user-1",
            company_id="company-1",
            parent_chat_id="chat-parent",
            subagent_message_id="m-mine",
        )

    assert question is not None
    assert question.elicitation_id == "mine"


async def test_find__nothing_asked__returns_none() -> None:
    with patch.object(
        Elicitation, "_static_request_async", new=AsyncMock(return_value=[])
    ):
        question = await find_subagent_question_async(
            user_id="user-1",
            company_id="company-1",
            parent_chat_id="chat-parent",
            subagent_message_id="m-mine",
        )

    assert question is None
