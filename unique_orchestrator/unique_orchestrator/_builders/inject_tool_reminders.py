"""Inject per-turn tool reminders as standalone user content parts.

Tools expose two per-turn hooks:

- :meth:`Tool.tool_system_reminder` — a ``<system-reminder>`` block
  describing the tool's current state (e.g. the Skill tool's listing
  of currently-available skills). Regenerated every loop iteration.
- :meth:`Tool.tool_description_for_user_prompt` — static per-turn
  description text the tool wants appended to the user message.

The orchestrator collects both, filters empties, and hands the list
to this module. We surface each string as its own
``{"type": "text"}`` entry on the latest user message, prepended
before the residual query text::

    {
      "role": "user",
      "content": [
        {"type": "text", "text": "<system-reminder>...skills...</system-reminder>"},
        {"type": "text", "text": "commit my staged changes"}
      ]
    }

This used to be done by rendering the reminders inline into the user
message string in ``user_message_prompt.jinja2`` and then
regex-extracting the ``<system-reminder>`` blocks back out in a
post-processing pass. That round-trip is unnecessary: we build the
parts directly here.

The user message may already be a multi-part list when this runs
(the open-file tool injects file parts before this step), so both
``str`` and ``list`` content shapes are supported. Non-text parts
(e.g. ``image_url``, ``file``) are preserved.
"""

from __future__ import annotations

from typing import Any

from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelUserMessage,
)


def _find_last_user_index(messages: LanguageModelMessages) -> int | None:
    for i in range(len(messages.root) - 1, -1, -1):
        if messages.root[i].role == LanguageModelMessageRole.USER:
            return i
    return None


def _content_as_parts(content: object) -> list[dict[str, Any]] | None:
    """Normalise a user-message ``content`` value to a parts list.

    Returns ``None`` when the content is neither a string nor a list
    of part dicts (i.e. nothing for us to process).
    """
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [p for p in content if isinstance(p, dict)]  # pyright: ignore[reportUnnecessaryIsInstance]
    return None


def inject_tool_reminders_into_user_message(
    messages: LanguageModelMessages,
    tool_reminders: list[str],
) -> LanguageModelMessages:
    """Prepend each non-empty ``tool_reminder`` as a text part.

    The reminders are inserted at the head of the latest user-role
    message's ``content`` array, in the order given, ahead of the
    residual query text and any other existing parts. Empty strings
    are skipped. Returns ``messages`` unchanged if there are no
    non-empty reminders or no user message in the stream.
    """
    non_empty_reminders = [r for r in tool_reminders if r]
    if not non_empty_reminders or not messages.root:
        return messages

    user_idx = _find_last_user_index(messages)
    if user_idx is None:
        return messages

    existing_parts = _content_as_parts(messages.root[user_idx].content)
    if existing_parts is None:
        return messages

    new_parts: list[dict[str, Any]] = [
        {"type": "text", "text": reminder} for reminder in non_empty_reminders
    ]
    new_parts.extend(existing_parts)
    messages.root[user_idx] = LanguageModelUserMessage(content=new_parts)
    return messages
