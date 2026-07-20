"""Tests for the chat-embed URL builder (mirrors the browser extension)."""

import pytest
from mcp_space_chat.embed import build_embed_url

pytestmark = pytest.mark.ai


def test_new_chat_url_has_no_chat_path_segment():
    url = build_embed_url("https://next.qa.unique.app", "assistant_abc")
    assert url == "https://next.qa.unique.app/chat/embed?spaceId=assistant_abc"


def test_existing_chat_url_includes_chat_id():
    url = build_embed_url("https://next.qa.unique.app", "assistant_abc", "chat_123")
    assert url == (
        "https://next.qa.unique.app/chat/embed/chat_123?spaceId=assistant_abc"
    )


def test_trailing_slash_on_base_url_is_normalized():
    url = build_embed_url("https://next.qa.unique.app/", "assistant_abc", "chat_123")
    assert url.startswith("https://next.qa.unique.app/chat/embed/chat_123")


def test_chat_id_is_url_encoded():
    url = build_embed_url("https://next.qa.unique.app", "assistant_abc", "chat/../x")
    assert "/chat/embed/chat%2F..%2Fx?" in url
