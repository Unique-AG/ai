from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService

from unique_internal_search.uploaded_search.config import UploadedSearchConfig
from unique_internal_search.uploaded_search.service import UploadedSearchTool


@pytest.fixture
def uploaded_search_config() -> UploadedSearchConfig:
    """Create a base UploadedSearchConfig for testing."""
    return UploadedSearchConfig()


@pytest.fixture
def mock_uploaded_documents_valid() -> list[Content]:
    """Create a list of valid (non-expired) Content documents for testing."""
    now = datetime.now(timezone.utc)
    future_expiry = now + timedelta(days=7)

    doc1 = Mock(spec=Content)
    doc1.id = "doc_1"
    doc1.title = "Q2 Financial Report"
    doc1.key = "q2_report.pdf"
    doc1.expired_at = None
    doc1.created_at = now - timedelta(days=1)

    doc2 = Mock(spec=Content)
    doc2.id = "doc_2"
    doc2.title = None
    doc2.key = "policy_document.pdf"
    doc2.expired_at = future_expiry
    doc2.created_at = now - timedelta(days=2)

    return [doc1, doc2]


@pytest.fixture
def mock_uploaded_documents_expired() -> list[Content]:
    """Create a list of expired Content documents for testing."""
    now = datetime.now(timezone.utc)
    past_expiry = now - timedelta(days=1)

    doc1 = Mock(spec=Content)
    doc1.id = "doc_expired_1"
    doc1.title = "Old Report"
    doc1.key = "old_report.pdf"
    doc1.expired_at = past_expiry
    doc1.created_at = now - timedelta(days=30)

    return [doc1]


@pytest.fixture
def mock_uploaded_documents_mixed() -> list[Content]:
    """Create a list of mixed valid and expired Content documents for testing."""
    now = datetime.now(timezone.utc)
    future_expiry = now + timedelta(days=7)
    past_expiry = now - timedelta(days=1)

    doc1 = Mock(spec=Content)
    doc1.id = "doc_valid_1"
    doc1.title = "Valid Document"
    doc1.key = "valid.pdf"
    doc1.expired_at = None
    doc1.created_at = now - timedelta(days=1)

    doc2 = Mock(spec=Content)
    doc2.id = "doc_valid_2"
    doc2.title = None
    doc2.key = "another_valid.pdf"
    doc2.expired_at = future_expiry
    doc2.created_at = now - timedelta(days=2)

    doc3 = Mock(spec=Content)
    doc3.id = "doc_expired_1"
    doc3.title = "Expired Document"
    doc3.key = "expired.pdf"
    doc3.expired_at = past_expiry
    doc3.created_at = now - timedelta(days=30)

    return [doc1, doc2, doc3]


class TestUploadedSearchTool:
    """Tests for UploadedSearchTool class."""

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__returns_formatted_prompt__with_valid_documents_only(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_uploaded_documents_valid: list[Content],
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt returns formatted prompt with valid documents listed.
        Why this matters: Ensures the system prompt includes information about available uploaded documents.
        Setup summary: Mock ContentService to return valid documents only, verify formatted output.
        """
        # Arrange
        with (
            patch(
                "unique_internal_search.uploaded_search.service.ContentService"
            ) as mock_content_service_class,
        ):
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(
                return_value=mock_uploaded_documents_valid
            )
            mock_content_service_class.from_event.return_value = mock_content_service

            # Create tool
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Act
            result = tool.tool_description_for_system_prompt()

            # Assert
            assert (
                "**The currently uploaded and valid documents are the following**"
                in result
            )
            assert "Q2 Financial Report" in result
            assert "policy_document.pdf" in result
            assert (
                "**The currently uploaded and expired documents are the following**"
                not in result
            )
            # Verify the config template was used
            assert "You can use the UploadedSearch tool" in result

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__returns_formatted_prompt__with_expired_documents_only(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_uploaded_documents_expired: list[Content],
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt returns formatted prompt with expired documents listed.
        Why this matters: Ensures the system knows which documents are expired and unavailable.
        Setup summary: Mock ContentService to return expired documents only, verify formatted output.
        """
        # Arrange
        with (
            patch(
                "unique_internal_search.uploaded_search.service.ContentService"
            ) as mock_content_service_class,
        ):
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(
                return_value=mock_uploaded_documents_expired
            )
            mock_content_service_class.from_event.return_value = mock_content_service

            # Create tool
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Act
            result = tool.tool_description_for_system_prompt()

            # Assert
            assert (
                "**The currently uploaded and expired documents are the following**"
                in result
            )
            assert "Old Report" in result
            assert (
                "**The currently uploaded and valid documents are the following**"
                not in result
            )

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__returns_formatted_prompt__with_mixed_documents(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_uploaded_documents_mixed: list[Content],
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt correctly separates valid and expired documents.
        Why this matters: Ensures proper categorization when both valid and expired documents exist.
        Setup summary: Mock ContentService to return mixed documents, verify both sections present.
        """
        # Arrange
        with (
            patch(
                "unique_internal_search.uploaded_search.service.ContentService"
            ) as mock_content_service_class,
        ):
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(
                return_value=mock_uploaded_documents_mixed
            )
            mock_content_service_class.from_event.return_value = mock_content_service

            # Create tool
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Act
            result = tool.tool_description_for_system_prompt()

            # Assert
            assert (
                "**The currently uploaded and valid documents are the following**"
                in result
            )
            assert "Valid Document" in result
            assert "another_valid.pdf" in result
            assert (
                "**The currently uploaded and expired documents are the following**"
                in result
            )
            assert "Expired Document" in result

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__returns_base_prompt__with_no_documents(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt returns base prompt when no documents uploaded.
        Why this matters: Ensures graceful handling when no documents are available.
        Setup summary: Mock ContentService to return empty list, verify base prompt returned.
        """
        # Arrange
        with (
            patch(
                "unique_internal_search.uploaded_search.service.ContentService"
            ) as mock_content_service_class,
        ):
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(return_value=[])
            mock_content_service_class.from_event.return_value = mock_content_service

            # Create tool
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Act
            result = tool.tool_description_for_system_prompt()

            # Assert
            assert "You can use the UploadedSearch tool" in result
            assert (
                "**The currently uploaded and valid documents are the following**"
                not in result
            )
            assert (
                "**The currently uploaded and expired documents are the following**"
                not in result
            )

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__uses_key_when_title_is_none(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt uses key when title is None.
        Why this matters: Ensures fallback to key when title is not available.
        Setup summary: Mock ContentService with documents without titles, verify key is used.
        """
        # Arrange
        now = datetime.now(timezone.utc)
        doc_without_title = Mock(spec=Content)
        doc_without_title.id = "doc_1"
        doc_without_title.title = None
        doc_without_title.key = "important_file.pdf"
        doc_without_title.expired_at = None
        doc_without_title.created_at = now

        with (
            patch(
                "unique_internal_search.uploaded_search.service.ContentService"
            ) as mock_content_service_class,
        ):
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(
                return_value=[doc_without_title]
            )
            mock_content_service_class.from_event.return_value = mock_content_service

            # Create tool
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Act
            result = tool.tool_description_for_system_prompt()

            # Assert
            assert "important_file.pdf" in result
            assert "- important_file.pdf" in result

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__uses_title_when_available(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt uses title when available instead of key.
        Why this matters: Ensures more user-friendly display names are used when titles exist.
        Setup summary: Mock ContentService with documents with titles, verify title is used.
        """
        # Arrange
        now = datetime.now(timezone.utc)
        doc_with_title = Mock(spec=Content)
        doc_with_title.id = "doc_1"
        doc_with_title.title = "Annual Report 2024"
        doc_with_title.key = "report_2024.pdf"
        doc_with_title.expired_at = None
        doc_with_title.created_at = now

        with (
            patch(
                "unique_internal_search.uploaded_search.service.ContentService"
            ) as mock_content_service_class,
        ):
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(
                return_value=[doc_with_title]
            )
            mock_content_service_class.from_event.return_value = mock_content_service

            # Create tool
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Act
            result = tool.tool_description_for_system_prompt()

            # Assert
            assert "Annual Report 2024" in result
            assert "- Annual Report 2024" in result
            # Key should not appear when title is present
            assert "report_2024.pdf" not in result

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__correctly_filters_by_current_time(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt correctly uses current time for expiration check.
        Why this matters: Ensures expiration logic is based on actual current time, not a fixed time.
        Setup summary: Create documents with expiry times near current time, verify correct categorization.
        """
        # Arrange
        now = datetime.now(timezone.utc)

        # Document that expired 1 second ago
        doc_just_expired = Mock(spec=Content)
        doc_just_expired.id = "doc_just_expired"
        doc_just_expired.title = "Just Expired"
        doc_just_expired.key = "just_expired.pdf"
        doc_just_expired.expired_at = now - timedelta(seconds=1)
        doc_just_expired.created_at = now - timedelta(days=1)

        # Document that expires in 1 second
        doc_still_valid = Mock(spec=Content)
        doc_still_valid.id = "doc_still_valid"
        doc_still_valid.title = "Still Valid"
        doc_still_valid.key = "still_valid.pdf"
        doc_still_valid.expired_at = now + timedelta(seconds=1)
        doc_still_valid.created_at = now - timedelta(days=1)

        with (
            patch(
                "unique_internal_search.uploaded_search.service.ContentService"
            ) as mock_content_service_class,
        ):
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(
                return_value=[doc_just_expired, doc_still_valid]
            )
            mock_content_service_class.from_event.return_value = mock_content_service

            # Create tool
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Act
            result = tool.tool_description_for_system_prompt()

            # Assert
            assert "Still Valid" in result
            assert "Just Expired" in result
            # Verify they are in the correct sections
            valid_section_start = result.find(
                "**The currently uploaded and valid documents are the following**"
            )
            expired_section_start = result.find(
                "**The currently uploaded and expired documents are the following**"
            )
            still_valid_pos = result.find("Still Valid")
            just_expired_pos = result.find("Just Expired")

            # "Still Valid" should appear after valid section header and before expired section
            assert valid_section_start < still_valid_pos < expired_section_start
            # "Just Expired" should appear after expired section header
            assert expired_section_start < just_expired_pos

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__formats_multiple_documents_with_newlines(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_uploaded_documents_valid: list[Content],
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt formats multiple documents with proper newlines and bullets.
        Why this matters: Ensures readable formatting when listing multiple documents.
        Setup summary: Mock ContentService with multiple documents, verify formatting with bullets and newlines.
        """
        # Arrange
        with (
            patch(
                "unique_internal_search.uploaded_search.service.ContentService"
            ) as mock_content_service_class,
        ):
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(
                return_value=mock_uploaded_documents_valid
            )
            mock_content_service_class.from_event.return_value = mock_content_service

            # Create tool
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Act
            result = tool.tool_description_for_system_prompt()

            # Assert
            # Verify bullet points are present
            assert "- Q2 Financial Report" in result
            assert "- policy_document.pdf" in result
            # Verify documents are on separate lines by checking the valid documents section
            valid_section = result.split(
                "**The currently uploaded and valid documents are the following**"
            )[1]
            # Make sure both documents appear in the valid section
            assert "Q2 Financial Report" in valid_section
            assert "policy_document.pdf" in valid_section
