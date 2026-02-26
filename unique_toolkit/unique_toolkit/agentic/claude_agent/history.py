"""
Conversation history text formatter for Claude Agent SDK integration.

Converts platform LanguageModelMessage history into a simple human-readable
text block that is injected into the system prompt. This matches Abi's Node
implementation where history is passed as a CHAT_HISTORY_SECTION string rather
than as structured Anthropic-format messages.

Future: structured Anthropic-format history (list of {role, content} dicts)
will be returned by _build_history() once the SDK streaming loop (Step 3) is
in place and we move past MVP.
"""

from __future__ import annotations

from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelUserMessage,
)

_MAX_MESSAGE_CHARS = 2000
_TRUNCATION_SUFFIX = "... [truncated]"


def format_history_as_text(
    messages: list[LanguageModelMessage],
    max_interactions: int,
) -> str:
    """Format conversation history as a readable text block for the system prompt.

    Args:
        messages: List of LanguageModelMessage objects from HistoryManager.
        max_interactions: Maximum number of user+assistant interaction pairs to
            include. The most recent pairs are kept.

    Returns:
        Formatted text with "User: ..." / "Assistant: ..." pairs separated by
        blank lines. Returns empty string when messages is empty or
        max_interactions is 0.
    """
    if not messages or max_interactions <= 0:
        return ""

    user_and_assistant = [
        m
        for m in messages
        if isinstance(m, (LanguageModelUserMessage, LanguageModelAssistantMessage))
    ]

    pairs: list[tuple[str, str]] = _pair_messages(user_and_assistant)

    # Keep only the most recent max_interactions pairs
    pairs = pairs[-max_interactions:]

    if not pairs:
        return ""

    formatted_pairs = [
        f"User: {_truncate(_extract_text(user_text))}\nAssistant: {_truncate(_extract_text(assistant_text))}"
        for user_text, assistant_text in pairs
    ]
    return "\n\n".join(formatted_pairs)


def _pair_messages(
    messages: list[LanguageModelMessage],
) -> list[tuple[str, str]]:
    """Group consecutive user+assistant messages into interaction pairs.

    Incomplete pairs (trailing user message without an assistant follow-up)
    are discarded — they represent the current in-flight turn.
    """
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if isinstance(msg, LanguageModelUserMessage):
            # Look ahead for a matching assistant reply
            if i + 1 < len(messages) and isinstance(
                messages[i + 1], LanguageModelAssistantMessage
            ):
                pairs.append((_get_content(msg), _get_content(messages[i + 1])))
                i += 2
                continue
        i += 1
    return pairs


def _get_content(message: LanguageModelMessage) -> str:
    """Extract raw content from a message as a string."""
    if message.content is None:
        return ""
    if isinstance(message.content, str):
        return message.content
    # list[dict] — e.g. multimodal content; stringify for history purposes
    import json

    return json.dumps(message.content)


def _extract_text(content: str) -> str:
    """Return content string, defaulting empty content to a placeholder."""
    return content if content else ""


def _truncate(text: str) -> str:
    """Truncate text to _MAX_MESSAGE_CHARS, appending a suffix when cut."""
    if len(text) <= _MAX_MESSAGE_CHARS:
        return text
    return text[:_MAX_MESSAGE_CHARS] + _TRUNCATION_SUFFIX
