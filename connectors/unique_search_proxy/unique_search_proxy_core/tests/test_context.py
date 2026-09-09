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

    def test_from_headers_uses_fallback_for_missing(self) -> None:
        context = RequestContext.from_headers(
            {COMPANY_ID_HEADER: "company-1"},
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert context.company_id == "company-1"
        assert context.user_id == "local"
        assert context.chat_id == "local"


@pytest.mark.ai
class TestRequestContextUserMetadata:
    def _context(self, user_metadata: dict[str, object] | None) -> RequestContext:
        return RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
            user_metadata=user_metadata,
        )

    def test_defaults_to_none(self) -> None:
        assert self._context(None).user_metadata is None

    def test_omits_header_when_metadata_is_empty(self) -> None:
        assert USER_METADATA_HEADER not in self._context(None).to_headers()
        assert USER_METADATA_HEADER not in self._context({}).to_headers()

    def test_round_trips_through_headers(self) -> None:
        metadata = {"userName": "u12345", "department": "research"}
        headers = self._context(metadata).to_headers()

        assert json.loads(headers[USER_METADATA_HEADER]) == metadata
        restored = RequestContext.from_headers(
            headers,
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert restored.user_metadata == metadata

    def test_serialized_header_is_latin_1_encodable(self) -> None:
        """HTTP headers are latin-1; non-ASCII metadata must not break transport."""
        headers = self._context({"userName": "Zoë Müller"}).to_headers()

        headers[USER_METADATA_HEADER].encode("latin-1")
        restored = RequestContext.from_headers(
            headers,
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert restored.user_metadata == {"userName": "Zoë Müller"}

    def test_metadata_is_not_a_required_context_header(self) -> None:
        missing = RequestContext.missing_headers(
            {
                COMPANY_ID_HEADER: "company-1",
                USER_ID_HEADER: "user-1",
                CHAT_ID_HEADER: "chat-1",
            }
        )
        assert missing == []

    @pytest.mark.parametrize("raw", ["not-json", '["list"]', '"string"'])
    def test_unusable_header_becomes_none_instead_of_raising(self, raw: str) -> None:
        """Callers needing an identity fail closed later; parsing must not 500."""
        context = RequestContext.from_headers(
            {
                COMPANY_ID_HEADER: "company-1",
                USER_ID_HEADER: "user-1",
                CHAT_ID_HEADER: "chat-1",
                USER_METADATA_HEADER: raw,
            },
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert context.user_metadata is None
