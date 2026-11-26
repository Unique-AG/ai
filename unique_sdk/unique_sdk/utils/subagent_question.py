"""A sub-agent's question that waits for the user in the parent chat.

A sub-agent turn runs in a hidden chat. The platform shows its elicitations in
the parent chat, and marks each one with the metadata below. The parent finds
the pending question through that metadata, tells the user's agent to wait for
it, and resumes the wait for the sub-agent afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass

from unique_sdk.api_resources._elicitation import Elicitation

META_SUBAGENT_NAME = "subAgentName"
META_SUBAGENT_CHAT_ID = "subAgentChatId"
META_SUBAGENT_MESSAGE_ID = "subAgentMessageId"


@dataclass(frozen=True)
class SubagentQuestion:
    """A pending elicitation that one sub-agent turn waits on."""

    elicitation_id: str
    message: str
    subagent_chat_id: str
    subagent_message_id: str


def as_subagent_question(
    elicitation: Elicitation.Elicitation,
) -> SubagentQuestion | None:
    """Read the sub-agent marks of an elicitation. None when it has none."""
    metadata = elicitation.get("metadata")
    if not isinstance(metadata, dict):
        return None
    chat_id = metadata.get(META_SUBAGENT_CHAT_ID)
    message_id = metadata.get(META_SUBAGENT_MESSAGE_ID)
    if not (isinstance(chat_id, str) and chat_id):
        return None
    if not (isinstance(message_id, str) and message_id):
        return None
    return SubagentQuestion(
        elicitation_id=elicitation["id"],
        message=elicitation.get("message", ""),
        subagent_chat_id=chat_id,
        subagent_message_id=message_id,
    )


async def find_subagent_question_async(
    *,
    user_id: str,
    company_id: str,
    parent_chat_id: str,
    subagent_message_id: str,
) -> SubagentQuestion | None:
    """Return the pending question of one sub-agent turn, if it asked one."""
    pending = await Elicitation.list_pending_async(
        user_id, company_id, chat_id=parent_chat_id
    )
    for elicitation in pending:
        question = as_subagent_question(elicitation)
        if question is None:
            continue
        if question.subagent_message_id == subagent_message_id:
            return question
    return None
