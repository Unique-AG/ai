"""Tests for tenant context header contract."""

from __future__ import annotations

import pytest

from unique_search_proxy_core.context import (
    CHAT_ID_HEADER,
    COMPANY_ID_HEADER,
    LOCAL_REQUEST_CONTEXT,
    USER_ID_HEADER,
    USER_NAME_HEADER,
    RequestContext,
)


@pytest.mark.ai
class TestRequestContext:
    def test_to_headers(self) -> None:
        context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
            user_name="jsmith",
        )
        assert context.to_headers() == {
            COMPANY_ID_HEADER: "company-1",
            USER_ID_HEADER: "user-1",
            CHAT_ID_HEADER: "chat-1",
            USER_NAME_HEADER: "jsmith",
        }

    def test_to_headers_omits_missing_user_name(self) -> None:
        assert USER_NAME_HEADER not in LOCAL_REQUEST_CONTEXT.to_headers()

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
        assert context.user_name is None

    def test_from_headers_reads_user_name(self) -> None:
        context = RequestContext.from_headers(
            {USER_NAME_HEADER: "jsmith"},
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        assert context.user_name == "jsmith"
