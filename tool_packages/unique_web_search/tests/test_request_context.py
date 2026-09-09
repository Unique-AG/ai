"""The tool hands the search proxy its tenant context, including user metadata."""

from typing import Any
from unittest.mock import Mock

import pytest
from unique_search_proxy_core.context import USER_METADATA_HEADER

from unique_web_search.service import WebSearchTool


def _build_tool(
    config: Mock,
    mocker: Any,
    user_metadata: dict[str, Any] | None,
) -> WebSearchTool:
    """Build a real tool from a chat event, stubbing only the outbound services."""
    event = Mock()
    event.company_id = "test-company"
    event.user_id = "test-user"
    event.payload.chat_id = "test-chat"
    event.payload.user_metadata = user_metadata

    mocker.patch("unique_web_search.service.get_search_engine_service")
    mocker.patch("unique_web_search.service.get_crawler_service")
    mocker.patch("unique_web_search.service.ChunkRelevancySorter")
    mocker.patch("unique_web_search.service.ContentProcessor")

    return WebSearchTool(
        config,
        event,
        chat_service=Mock(get_full_history=Mock(return_value=[])),
        language_model_service=Mock(),
    )


@pytest.mark.ai
class TestRequestContextUserMetadata:
    def test_passes_user_metadata_through_untouched(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """No field is singled out here: which field identifies the user is proxy config."""
        user_metadata = {
            "userName": "u12345",
            "email": "user@example.com",
            "department": "research",
        }

        tool = _build_tool(mock_web_search_config_v1, mocker, user_metadata)

        assert tool.request_context.user_metadata == user_metadata

    def test_metadata_reaches_the_proxy_as_a_header(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        tool = _build_tool(
            mock_web_search_config_v1,
            mocker,
            {"userName": "u12345"},
        )

        assert USER_METADATA_HEADER in tool.request_context.to_headers()

    def test_tolerates_events_without_user_metadata(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        tool = _build_tool(mock_web_search_config_v1, mocker, None)

        assert tool.request_context.user_metadata is None
        assert tool.request_context.company_id == "test-company"

    def test_still_carries_the_existing_tenant_identifiers(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        tool = _build_tool(
            mock_web_search_config_v1,
            mocker,
            {"userName": "u12345"},
        )

        assert tool.request_context.company_id == "test-company"
        assert tool.request_context.user_id == "test-user"
        assert tool.request_context.chat_id == "test-chat"
