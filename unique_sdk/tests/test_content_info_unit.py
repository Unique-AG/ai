"""Unit tests for ``Content`` search / content-info TypedDict shapes."""

from __future__ import annotations

import unique_sdk


def test_AI_content_where_input_accepts_parent_id_filter():
    """Public ContentWhereInput includes parentId (StringNullableFilter)."""
    where: unique_sdk.Content.ContentWhereInput = {
        "parentId": {"equals": "scope_123"},
    }
    assert where["parentId"] == {"equals": "scope_123"}


def test_AI_content_info_matches_nullable_metric_fields():
    """Content info payloads may null byteSize, mimeType, ownerId, ingestionState."""
    row: unique_sdk.Content.ContentInfo = {
        "id": "cont_1",
        "key": "doc.pdf",
        "url": None,
        "title": None,
        "description": None,
        "metadata": {"k": "v"},
        "byteSize": None,
        "mimeType": None,
        "ownerId": None,
        "ingestionState": None,
        "createdAt": "2021-01-01T00:00:00.000Z",
        "updatedAt": "2021-01-01T00:00:00.000Z",
        "expiresAt": None,
        "deletedAt": None,
        "expiredAt": None,
        "object": "content-info",
    }
    assert row["byteSize"] is None
    assert row.get("object") == "content-info"


def test_AI_paginated_content_infos_optional_object_discriminator():
    """List endpoints may include an object tag (e.g. content-infos)."""
    page: unique_sdk.Content.PaginatedContentInfos = {
        "contentInfos": [],
        "totalCount": 0,
        "object": "content-infos",
    }
    assert page["object"] == "content-infos"
