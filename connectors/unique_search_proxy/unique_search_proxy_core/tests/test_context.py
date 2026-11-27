"""Tests for tenant context header contract."""

from __future__ import annotations

import json

import pytest

from unique_search_proxy_core.context import (
    CHAT_ID_HEADER,
    COMPANY_ID_HEADER,
    ENTRY_POINT_HEADER,
    LOCAL_REQUEST_CONTEXT,
    MESSAGE_ID_HEADER,
    SERVICE_ID_HEADER,
    USER_ID_HEADER,
    USER_METADATA_HEADER,
    EntryPoint,
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


@pytest.mark.ai
class TestEntryPointAndAttribution:
    def test_message_id_is_optional_and_round_trips_through_headers(self) -> None:
        assert MESSAGE_ID_HEADER not in LOCAL_REQUEST_CONTEXT.to_headers()
        context = LOCAL_REQUEST_CONTEXT.model_copy(update={"message_id": "msg-1"})
        headers = context.to_headers()
        assert headers[MESSAGE_ID_HEADER] == "msg-1"
        restored = RequestContext.from_headers(headers, fallback=LOCAL_REQUEST_CONTEXT)
        assert restored.message_id == "msg-1"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_message_id_header_uses_fallback(self, raw: str) -> None:
        fallback = LOCAL_REQUEST_CONTEXT.model_copy(update={"message_id": "fallback"})
        context = RequestContext.from_headers(
            {MESSAGE_ID_HEADER: raw}, fallback=fallback
        )
        assert context.message_id == "fallback"

    def test_unknown_entry_point_emits_no_header(self) -> None:
        headers = LOCAL_REQUEST_CONTEXT.to_headers()
        assert ENTRY_POINT_HEADER not in headers

    def test_entry_point_round_trips_through_headers(self) -> None:
        context = RequestContext(
            company_id="1",
            user_id="2",
            chat_id="chat-1",
            entry_point=EntryPoint.CHAT_TOOL,
        )
        headers = context.to_headers()
        assert headers[ENTRY_POINT_HEADER] == "chat_tool"
        restored = RequestContext.from_headers(headers, fallback=LOCAL_REQUEST_CONTEXT)
        assert restored.entry_point is EntryPoint.CHAT_TOOL

    @pytest.mark.parametrize("raw", ["not-a-service", "", "CHAT_TOOL "])
    def test_unrecognised_entry_point_becomes_unknown(self, raw: str) -> None:
        context = RequestContext.from_headers(
            {ENTRY_POINT_HEADER: raw},
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert context.entry_point is EntryPoint.UNKNOWN

    def test_absent_entry_point_uses_fallback(self) -> None:
        fallback = RequestContext(
            company_id="local",
            user_id="local",
            chat_id="local",
            entry_point=EntryPoint.DEEP_RESEARCH,
        )
        context = RequestContext.from_headers({}, fallback=fallback)
        assert context.entry_point is EntryPoint.DEEP_RESEARCH

    @pytest.mark.parametrize(
        ("company_id", "user_id", "invalid"),
        [
            ("123456789012345678", "987654321098765432", []),
            ("local", "123", [COMPANY_ID_HEADER]),
            ("123", "", [USER_ID_HEADER]),
            ("company-1", "user-1", [COMPANY_ID_HEADER, USER_ID_HEADER]),
            ("１２３", "123", [COMPANY_ID_HEADER]),
        ],
    )
    def test_is_attributed_requires_numeric_company_and_user(
        self,
        company_id: str,
        user_id: str,
        invalid: list[str],
    ) -> None:
        context = RequestContext(
            company_id=company_id,
            user_id=user_id,
            chat_id="local",
        )
        assert context.invalid_identity_headers == invalid
        assert context.is_attributed == (not invalid)

    def test_unknown_entry_point_still_counts_as_attributed(self) -> None:
        context = RequestContext(company_id="1", user_id="2", chat_id="local")
        assert context.entry_point is EntryPoint.UNKNOWN
        assert context.is_attributed

    @pytest.mark.parametrize(
        ("headers", "caller"),
        [
            ({SERVICE_ID_HEADER: "node-chat"}, "node-chat"),
            ({SERVICE_ID_HEADER: ""}, "unknown"),
            ({}, "unknown"),
        ],
    )
    def test_caller_is_read_from_service_id_header_but_never_sent(
        self,
        headers: dict[str, str],
        caller: str,
    ) -> None:
        context = RequestContext.from_headers(headers, fallback=LOCAL_REQUEST_CONTEXT)
        assert context.caller == caller
        assert SERVICE_ID_HEADER not in context.to_headers()
