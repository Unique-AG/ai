import logging
from typing import Optional

import unique_sdk

from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.utils import count_tokens


def convert_chat_history_to_injectable_string(
    history: list[ChatMessage],
) -> tuple[list[str], int]:
    """
    Converts chat history to a string that can be injected into the model.

    Args:
        history (list[ChatMessage]): The chat history.

    Returns:
        tuple[list[str], int]: The chat history and the token length of the chat context.
    """
    chatHistory = []
    for msg in history:
        if msg.role.value == "assistant":
            chatHistory.append(f"previous_answer: {msg.content}")
        else:
            chatHistory.append(f"previous_question: {msg.content}")
    chatContext = "\n".join(chatHistory)
    chatContextTokenLength = count_tokens(chatContext)
    return chatHistory, chatContextTokenLength


def map_references(references: list[ContentReference]) -> list[dict]:
    """Maps ContentReference objects to dictionary format for SDK calls."""
    return [
        {
            "name": ref.name,
            "url": ref.url,
            "sequenceNumber": ref.sequence_number,
            "sourceId": ref.source_id,
            "source": ref.source,
        }
        for ref in references
    ]


def filter_valid_messages(
    messages: unique_sdk.ListObject[unique_sdk.Message],
) -> list[dict]:
    """Filters out system messages and invalid messages from the message list."""
    SYSTEM_MESSAGE_PREFIX = "[SYSTEM] "

    # Remove the last two messages
    messages = messages["data"][:-2]  # type: ignore
    filtered_messages = []
    for message in messages:
        if message["text"] is None:
            continue
        elif SYSTEM_MESSAGE_PREFIX in message["text"]:
            continue
        else:
            filtered_messages.append(message)

    return filtered_messages


def map_to_chat_messages(messages: list[dict]) -> list[ChatMessage]:
    """Converts raw message dictionaries to ChatMessage objects."""
    return [ChatMessage(**msg) for msg in messages]


def pick_messages_in_reverse_for_token_window(
    messages: list[ChatMessage],
    limit: int,
    logger: Optional[logging.Logger] = None,
) -> list[ChatMessage]:
    """Selects messages that fit within the token limit, starting from the most recent."""
    if len(messages) < 1 or limit < 1:
        return []

    last_index = len(messages) - 1
    token_count = count_tokens(messages[last_index].content)
    while token_count > limit:
        if logger:
            logger.debug(
                f"Limit too low for the initial message. Last message TokenCount {token_count} available tokens {limit} - cutting message in half until it fits"
            )
        content = messages[last_index].content
        messages[last_index].content = content[: len(content) // 2] + "..."
        token_count = count_tokens(messages[last_index].content)

    while token_count <= limit and last_index > 0:
        token_count = count_tokens(
            "".join([msg.content for msg in messages[:last_index]])
        )
        if token_count <= limit:
            last_index -= 1

    last_index = max(0, last_index)
    return messages[last_index:]
