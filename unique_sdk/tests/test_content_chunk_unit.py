"""Unit tests for ``Content.Chunk`` TypedDict (public API / GraphQL parity)."""

from __future__ import annotations

import unique_sdk


def test_AI_content_chunk_accepts_minimal_embedded_search_shape():
    """Embedded chunk hits may only expose id, text, and page metadata."""
    minimal: unique_sdk.Content.Chunk = {
        "id": "chunk_1",
        "text": "body",
        "startPage": 1,
        "endPage": 1,
        "order": 0,
    }
    assert minimal["id"] == "chunk_1"


def test_AI_content_chunk_accepts_full_public_chunk_shape():
    """Full chunk records include contentId, timestamps, model, and object."""
    full: unique_sdk.Content.Chunk = {
        "id": "chunk_1",
        "text": "body",
        "contentId": "cont_1",
        "createdAt": "2021-01-01T00:00:00.000Z",
        "updatedAt": "2021-01-01T00:00:00.000Z",
        "object": "chunk",
        "startPage": 1,
        "endPage": 2,
        "order": 0,
        "model": "text-embedding-3-small",
    }
    assert full["contentId"] == "cont_1"
    assert full["object"] == "chunk"
