"""Tests for tenant context header contract."""

from __future__ import annotations

import json

import pytest

from unique_search_proxy_core.context import (
    CHAT_ID_HEADER,
    COMPANY_ID_HEADER,
    LOCAL_REQUEST_CONTEXT,
    USER_ID_HEADER,
    USER_METADATA_HEADER,
    RequestContext,
)


@pytest.mark.ai
class TestRequestContext:
    def test_to_headers(self) -> None:
        context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
        )
        assert context.to_headers() == {
            COMPANY_ID_HEADER: "company-1",
            USER_ID_HEADER: "user-1",
            CHAT_ID_HEADER: "chat-1",
        }

    def test_user_metadata_defaults_to_empty_dict(self) -> None:
        context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
        )
        assert context.user_metadata == {}

    def test_empty_user_metadata_emits_no_header(self) -> None:
        context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
            user_metadata={},
        )
        assert USER_METADATA_HEADER not in context.to_headers()

    def test_user_metadata_round_trips_through_headers(self) -> None:
        metadata = {"userName": "u12345", "email": "a@b.com"}
        context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
            user_metadata=metadata,
        )
        headers = context.to_headers()
        assert json.loads(headers[USER_METADATA_HEADER]) == metadata

        restored = RequestContext.from_headers(
            headers,
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert restored.user_metadata == metadata

    def test_user_metadata_header_is_latin1_encodable(self) -> None:
        context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
            user_metadata={"displayName": "José"},
        )
        headers = context.to_headers()
        headers[USER_METADATA_HEADER].encode("latin-1")

    def test_malformed_user_metadata_header_becomes_empty_dict(self) -> None:
        context = RequestContext.from_headers(
            {
                COMPANY_ID_HEADER: "company-1",
                USER_ID_HEADER: "user-1",
                CHAT_ID_HEADER: "chat-1",
                USER_METADATA_HEADER: "{not-json",
            },
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert context.user_metadata == {}

    def test_non_object_user_metadata_header_becomes_empty_dict(self) -> None:
        context = RequestContext.from_headers(
            {
                COMPANY_ID_HEADER: "company-1",
                USER_ID_HEADER: "user-1",
                CHAT_ID_HEADER: "chat-1",
                USER_METADATA_HEADER: json.dumps(["not", "an", "object"]),
            },
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert context.user_metadata == {}

    def test_absent_user_metadata_header_uses_fallback(self) -> None:
        fallback = RequestContext(
            company_id="local",
            user_id="local",
            chat_id="local",
            user_metadata={"userName": "fallback"},
        )
        context = RequestContext.from_headers(
            {
                COMPANY_ID_HEADER: "company-1",
                USER_ID_HEADER: "user-1",
                CHAT_ID_HEADER: "chat-1",
            },
            fallback=fallback,
        )
        assert context.user_metadata == {"userName": "fallback"}

    def test_missing_headers_detects_absent_values(self) -> None:
        missing = RequestContext.missing_headers(
            {
                COMPANY_ID_HEADER: "company-1",
                USER_ID_HEADER: "",
            }
        )
        assert USER_ID_HEADER in missing
        assert CHAT_ID_HEADER in missing
        assert COMPANY_ID_HEADER not in missing
        assert USER_METADATA_HEADER not in missing

    def test_from_headers_uses_fallback_for_missing(self) -> None:
        context = RequestContext.from_headers(
            {COMPANY_ID_HEADER: "company-1"},
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert context.company_id == "company-1"
        assert context.user_id == "local"
        assert context.chat_id == "local"
        assert context.user_metadata == {}
