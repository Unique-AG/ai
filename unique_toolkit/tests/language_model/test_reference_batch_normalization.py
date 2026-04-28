"""Tests for batch reference preprocessing shared with the streaming pattern replacer."""

from __future__ import annotations

import pytest

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.reference import add_references_to_message


def _chunk(suffix: str, title: str) -> ContentChunk:
    return ContentChunk(
        id=f"cont_{suffix}",
        key=f"key_{suffix}",
        title=title,
        text="body",
        order=0,
    )


@pytest.mark.ai
def test_add_references_to_message__normalizes_bracket_source_alias():
    """
    Purpose: ``[source 1]`` in assistant text becomes a resolved footnote for chunk 1.
    Why this matters: Batch path must share ``BATCH_NORMALIZATION_PATTERNS`` with streaming so citations match.
    Setup summary: One chunk; message content ``See [source 1]``; expect ``<sup>`` and one reference.
    """
    chunks = [_chunk("aaaaaaaaaaaaaaaaaaaaaaaa", "Alpha")]
    msg = ChatMessage(
        id="m1",
        chat_id="c1",
        role=ChatMessageRole.ASSISTANT,
        content="See [source 1] please.",
    )
    updated, changed = add_references_to_message(msg, chunks)
    assert changed is True
    assert "<sup>" in (updated.content or "")
    assert "[source 1]" not in (updated.content or "")
    assert updated.references is not None
    assert len(updated.references) == 1
    assert updated.references[0].name == "Alpha"


@pytest.mark.ai
def test_add_references_to_message__strips_placeholder_conversation_tags():
    """
    Purpose: Model-emitted ``[<user>]``-style placeholders are removed before reference parsing.
    Why this matters: Those tokens are not real citations and would confuse users if left in place.
    Setup summary: Content includes ``[<user>]``; no matching chunk needed; placeholder removed from output.
    """
    chunks: list[ContentChunk] = []
    msg = ChatMessage(
        id="m2",
        chat_id="c1",
        role=ChatMessageRole.ASSISTANT,
        content="Hello [<user>] there.",
    )
    updated, changed = add_references_to_message(msg, chunks)
    assert changed is False
    assert "[<user>]" not in (updated.content or "")
    assert "Hello" in (updated.content or "")
