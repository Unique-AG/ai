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

    doc1 = Content(
        id="doc_1", key="q2_report.pdf", title="Q2 Financial Report", expired_at=None
    )
    doc2 = Content(
        id="doc_2", key="policy_document.pdf", title=None, expired_at=future_expiry
    )

    return [doc1, doc2]


@pytest.fixture
def mock_uploaded_documents_expired() -> list[Content]:
    """Create a list of expired Content documents for testing."""
    now = datetime.now(timezone.utc)
    past_expiry = now - timedelta(days=1)

    doc1 = Content(
        id="doc_expired_1",
        key="old_report.pdf",
        title="Old Report",
        expired_at=past_expiry,
    )

    return [doc1]


@pytest.fixture
def mock_uploaded_documents_mixed() -> list[Content]:
    """Create a list of mixed valid and expired Content documents for testing."""
    now = datetime.now(timezone.utc)
    future_expiry = now + timedelta(days=7)
    past_expiry = now - timedelta(days=1)

    doc1 = Content(
        id="doc_valid_1", key="valid.pdf", title="Valid Document", expired_at=None
    )
    doc2 = Content(
        id="doc_valid_2", key="another_valid.pdf", title=None, expired_at=future_expiry
    )
    doc3 = Content(
        id="doc_expired_1",
        key="expired.pdf",
        title="Expired Document",
        expired_at=past_expiry,
    )

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
            assert "Q2 Financial Report (content_id: doc_1)" in result
            assert "policy_document.pdf (content_id: doc_2)" in result
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
            assert "Old Report (content_id: doc_expired_1)" in result
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
            assert "Valid Document (content_id: doc_valid_1)" in result
            assert "another_valid.pdf (content_id: doc_valid_2)" in result
            assert (
                "**The currently uploaded and expired documents are the following**"
                in result
            )
            assert "Expired Document (content_id: doc_expired_1)" in result

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
        doc_without_title = Content(
            id="doc_1", key="important_file.pdf", title=None, expired_at=None
        )

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
            assert "important_file.pdf (content_id: doc_1)" in result
            assert "- important_file.pdf (content_id: doc_1)" in result

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
        doc_with_title = Content(
            id="doc_1",
            key="report_2024.pdf",
            title="Annual Report 2024",
            expired_at=None,
        )

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
            assert "Annual Report 2024 (content_id: doc_1)" in result
            assert "- Annual Report 2024 (content_id: doc_1)" in result
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
        doc_just_expired = Content(
            id="doc_just_expired",
            key="just_expired.pdf",
            title="Just Expired",
            expired_at=now - timedelta(seconds=1),
        )

        # Document that expires in 1 second
        doc_still_valid = Content(
            id="doc_still_valid",
            key="still_valid.pdf",
            title="Still Valid",
            expired_at=now + timedelta(seconds=1),
        )

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
            assert "- Q2 Financial Report (content_id: doc_1)" in result
            assert "- policy_document.pdf (content_id: doc_2)" in result
            # Verify documents are on separate lines by checking the valid documents section
            valid_section = result.split(
                "**The currently uploaded and valid documents are the following**"
            )[1]
            # Make sure both documents appear in the valid section
            assert "Q2 Financial Report" in valid_section
            assert "policy_document.pdf" in valid_section

    @pytest.mark.ai
    def test_display_name__returns_uploaded_search(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify display_name() returns the correct display name "Uploaded Search".
        Why this matters: Ensures the tool has a user-friendly display name for UI/UX purposes.
        Setup summary: Create tool and verify display_name() method returns expected value.
        """
        # Arrange
        with patch(
            "unique_internal_search.uploaded_search.service.ContentService"
        ) as mock_content_service_class:
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(return_value=[])
            mock_content_service_class.from_event.return_value = mock_content_service

            # Act
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Assert
            assert tool.display_name() == "Uploaded Search"
            assert tool._display_name == "Uploaded Search"

    @pytest.mark.ai
    def test_init__sets_display_name_on_internal_search_tool(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify that the display name is propagated to the internal search tool during initialization.
        Why this matters: Ensures consistent display naming across the tool hierarchy.
        Setup summary: Create tool and verify internal search tool has the same display name.
        """
        # Arrange
        with patch(
            "unique_internal_search.uploaded_search.service.ContentService"
        ) as mock_content_service_class:
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(return_value=[])
            mock_content_service_class.from_event.return_value = mock_content_service

            # Act
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )

            # Assert
            assert hasattr(tool._internal_search_tool, "_display_name")
            assert tool._internal_search_tool._display_name == "Uploaded Search"
            assert tool._internal_search_tool._display_name == tool._display_name

    @pytest.mark.ai
    def test_class_attribute_display_name__is_set_correctly(
        self,
    ) -> None:
        """
        Purpose: Verify that the _display_name class attribute is set to "Uploaded Search".
        Why this matters: Ensures the class-level display name is properly defined.
        Setup summary: Check class attribute without instantiation.
        """
        # Act & Assert
        assert UploadedSearchTool._display_name == "Uploaded Search"
        assert hasattr(UploadedSearchTool, "_display_name")


@pytest.mark.ai
class TestToolDescriptionForSystemPromptIngestionFilter:
    """Tests for ingestion filtering in tool_description_for_system_prompt.

    Docs whose is_ingested() returns False (e.g. SKIP_INGESTION mode) must be
    excluded from both the valid and expired document lists in the system prompt.
    """

    def _make_tool(
        self,
        documents: list[Content],
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event,
        mock_tool_progress_reporter,
    ) -> UploadedSearchTool:
        with patch(
            "unique_internal_search.uploaded_search.service.ContentService"
        ) as mock_content_service_class:
            mock_content_service = Mock(spec=ContentService)
            mock_content_service.get_documents_uploaded_to_chat = Mock(
                return_value=documents
            )
            mock_content_service_class.from_event.return_value = mock_content_service
            tool = UploadedSearchTool(
                config=uploaded_search_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
            )
        return tool

    @pytest.mark.ai
    def test_skip_ingestion_doc_excluded_from_valid_section(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event,
        mock_tool_progress_reporter,
    ) -> None:
        """
        Purpose: Verify that a doc with SKIP_INGESTION mode does not appear in
                 the valid documents section of the system prompt.
        Why this matters: Non-ingested docs cannot be searched, so surfacing them
                          as "valid" would mislead the model into attempting searches
                          that would return no results.
        Setup summary: Create a Content with SKIP_INGESTION applied_ingestion_config
                       and expired_at=None; assert neither the doc name nor the valid
                       section header appears in the rendered prompt.
        """
        skip_doc = Content(
            id="skip_1",
            key="skip_doc.pdf",
            title="Skipped Document",
            expired_at=None,
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_INGESTION"},
        )

        tool = self._make_tool(
            [skip_doc],
            uploaded_search_config,
            mock_chat_event,
            mock_tool_progress_reporter,
        )
        result = tool.tool_description_for_system_prompt()

        assert "Skipped Document" not in result
        assert (
            "**The currently uploaded and valid documents are the following**"
            not in result
        )

    @pytest.mark.ai
    def test_skip_ingestion_doc_excluded_from_expired_section(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event,
        mock_tool_progress_reporter,
    ) -> None:
        """
        Purpose: Verify that a doc with SKIP_INGESTION mode does not appear in
                 the expired documents section even when its expired_at is in the past.
        Why this matters: Docs skipped from ingestion should be invisible in all
                          sections of the system prompt regardless of their expiry state.
        Setup summary: Create a Content with SKIP_INGESTION and a past expired_at;
                       assert the doc name and the expired section header are absent.
        """
        now = datetime.now(timezone.utc)
        past_expiry = now - timedelta(days=1)

        skip_expired_doc = Content(
            id="skip_expired_1",
            key="skip_expired.pdf",
            title="Skipped Expired Document",
            expired_at=past_expiry,
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_INGESTION"},
        )

        tool = self._make_tool(
            [skip_expired_doc],
            uploaded_search_config,
            mock_chat_event,
            mock_tool_progress_reporter,
        )
        result = tool.tool_description_for_system_prompt()

        assert "Skipped Expired Document" not in result
        assert (
            "**The currently uploaded and expired documents are the following**"
            not in result
        )

    @pytest.mark.ai
    def test_ingested_doc_still_appears_when_mixed_with_skip_ingestion_doc(
        self,
        uploaded_search_config: UploadedSearchConfig,
        mock_chat_event,
        mock_tool_progress_reporter,
    ) -> None:
        """
        Purpose: Verify that ingested docs still appear in the prompt when mixed
                 with non-ingested (SKIP_INGESTION) docs.
        Why this matters: The ingestion filter must only suppress non-ingested docs —
                          valid ingested docs must remain visible.
        Setup summary: Mix one SKIP_INGESTION doc with one normally-ingested doc
                       (applied_ingestion_config=None); assert only the ingested doc
                       appears in the valid section.
        """
        skip_doc = Content(
            id="skip_2",
            key="skip_file.pdf",
            title="Skipped File",
            expired_at=None,
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_INGESTION"},
        )
        ingested_doc = Content(
            id="ingested_1",
            key="ingested_file.pdf",
            title="Ingested File",
            expired_at=None,
            applied_ingestion_config=None,
        )

        tool = self._make_tool(
            [skip_doc, ingested_doc],
            uploaded_search_config,
            mock_chat_event,
            mock_tool_progress_reporter,
        )
        result = tool.tool_description_for_system_prompt()

        assert "Ingested File (content_id: ingested_1)" in result
        assert "Skipped File" not in result
        assert (
            "**The currently uploaded and valid documents are the following**" in result
        )
