from datetime import datetime
from pathlib import Path, PurePath
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
import unique_sdk

from unique_toolkit.app.schemas import (
    BaseEvent,
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    Event,
    EventName,
    EventPayload,
)
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import (
    BaseFolderInfo,
    Content,
    ContentChunk,
    ContentInfo,
    ContentRerankerConfig,
    ContentSearchType,
    DeleteContentResponse,
    FolderInfo,
    PaginatedContentInfos,
)
from unique_toolkit.services.knowledge_base import KnowledgeBaseService


@pytest.fixture
def base_kb_service() -> KnowledgeBaseService:
    """
    Base fixture for KnowledgeBaseService with test credentials.
    """
    return KnowledgeBaseService(
        company_id="test_company",
        user_id="test_user",
        metadata_filter=None,
    )


@pytest.fixture
def kb_service_with_metadata() -> KnowledgeBaseService:
    """
    KnowledgeBaseService with metadata filter.
    """
    return KnowledgeBaseService(
        company_id="test_company",
        user_id="test_user",
        metadata_filter={"key": "test_value"},
    )


@pytest.fixture
def mock_content_chunk() -> ContentChunk:
    """
    Mock ContentChunk for testing.
    """
    return ContentChunk(
        id="cont_test123",
        text="Test chunk text",
        order=1,
        key="test_file.txt",
    )


@pytest.fixture
def mock_content() -> Content:
    """
    Mock Content for testing.
    """
    return Content(
        id="cont_test123",
        key="test_file.txt",
        title="Test File",
        chunks=[],
    )


@pytest.fixture
def mock_content_info() -> ContentInfo:
    """
    Mock ContentInfo for testing.
    """
    return ContentInfo(
        id="cont_test123",
        object="content",
        key="test_file.txt",
        byte_size=100,
        mime_type="text/plain",
        owner_id="test_user",
        created_at=datetime(2024, 1, 1, 0, 0, 0),
        updated_at=datetime(2024, 1, 1, 0, 0, 0),
    )


@pytest.fixture
def mock_folder_info() -> FolderInfo:
    """
    Mock FolderInfo for testing.
    """
    return FolderInfo(
        id="scope_test123",
        name="test_folder",
        parent_id=None,
        ingestion_config={},
        created_at=None,
        updated_at=None,
        external_id=None,
    )


@pytest.fixture
def mock_base_folder_info() -> BaseFolderInfo:
    """
    Mock BaseFolderInfo for testing.
    """
    return BaseFolderInfo(
        id="scope_test123",
        name="test_folder",
        parent_id=None,
    )


@pytest.fixture
def mock_event() -> Event:
    """
    Mock Event for testing from_event initialization.
    """
    return Event(
        id="event_test123",
        company_id="test_company",
        user_id="test_user",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        payload=EventPayload(
            name="test_module",
            description="Test description",
            configuration={},
            chat_id="test_chat",
            assistant_id="test_assistant",
            user_message=ChatEventUserMessage(
                id="user_msg_123",
                text="test",
                original_text="test",
                created_at="2024-01-01T00:00:00Z",
                language="english",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="asst_msg_123",
                created_at="2024-01-01T00:00:00Z",
            ),
            metadata_filter={"key": "test_value"},
        ),
    )


@pytest.fixture
def mock_chat_event() -> ChatEvent:
    """
    Mock ChatEvent for testing from_event initialization.
    """
    return ChatEvent(
        id="event_test123",
        company_id="test_company",
        user_id="test_user",
        event=EventName.USER_MESSAGE_CREATED,
        payload=ChatEventPayload(
            name="test_module",
            description="Test description",
            configuration={},
            metadata_filter={"key": "test_value"},
            chat_id="test_chat",
            assistant_id="test_assistant",
            user_message=ChatEventUserMessage(
                id="user_msg_123",
                text="test",
                original_text="test",
                created_at="2024-01-01T00:00:00Z",
                language="english",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="asst_msg_123",
                created_at="2024-01-01T00:00:00Z",
            ),
        ),
    )


class TestKnowledgeBaseServiceInitialization:
    """Test cases for KnowledgeBaseService initialization."""

    @pytest.mark.ai
    def test_init__creates_service__with_company_and_user_id(
        self, base_kb_service: KnowledgeBaseService
    ) -> None:
        """
        Purpose: Verify KnowledgeBaseService initializes with company_id and user_id.
        Why this matters: Core initialization must work correctly for all operations.
        Setup summary: Create service with test credentials, assert attributes are set.
        """
        # Assert
        assert base_kb_service._company_id == "test_company"
        assert base_kb_service._user_id == "test_user"
        assert base_kb_service._metadata_filter is None

    @pytest.mark.ai
    def test_init__sets_metadata_filter__when_provided(
        self, kb_service_with_metadata: KnowledgeBaseService
    ) -> None:
        """
        Purpose: Verify metadata_filter is correctly stored during initialization.
        Why this matters: Metadata filtering is essential for scoped searches.
        Setup summary: Create service with metadata_filter, assert it's stored.
        """
        # Assert
        assert kb_service_with_metadata._metadata_filter == {"key": "test_value"}

    @pytest.mark.ai
    def test_from_event__creates_service__with_event_metadata(
        self, mock_event: Event
    ) -> None:
        """
        Purpose: Verify from_event classmethod extracts credentials and metadata from Event.
        Why this matters: Enables service creation from event context.
        Setup summary: Create Event with metadata, use from_event, assert correct initialization.
        """
        # Act
        service = KnowledgeBaseService.from_event(mock_event)

        # Assert
        assert service._company_id == "test_company"
        assert service._user_id == "test_user"
        assert service._metadata_filter == {"key": "test_value"}

    @pytest.mark.ai
    def test_from_event__creates_service__with_chat_event_metadata(
        self, mock_chat_event: ChatEvent
    ) -> None:
        """
        Purpose: Verify from_event works with ChatEvent and extracts metadata_filter.
        Why this matters: ChatEvent is a common event type that should be supported.
        Setup summary: Create ChatEvent with metadata, use from_event, assert correct initialization.
        """
        # Act
        service = KnowledgeBaseService.from_event(mock_chat_event)

        # Assert
        assert service._company_id == "test_company"
        assert service._user_id == "test_user"
        assert service._metadata_filter == {"key": "test_value"}

    @pytest.mark.ai
    def test_from_event__creates_service__with_base_event_no_metadata(
        self,
    ) -> None:
        """
        Purpose: Verify from_event handles BaseEvent without metadata_filter gracefully.
        Why this matters: BaseEvent may not have metadata_filter, service should handle this.
        Setup summary: Create BaseEvent without metadata, use from_event, assert metadata_filter is None.
        """
        # Arrange
        base_event = BaseEvent(
            id="test_id",
            company_id="test_company",
            user_id="test_user",
            event=EventName.EXTERNAL_MODULE_CHOSEN,
        )

        # Act
        service = KnowledgeBaseService.from_event(base_event)

        # Assert
        assert service._company_id == "test_company"
        assert service._user_id == "test_user"
        assert service._metadata_filter is None

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.UniqueSettings")
    def test_from_settings__creates_service__with_default_settings(
        self, mock_settings_class: Mock
    ) -> None:
        """
        Purpose: Verify from_settings creates service using default settings initialization.
        Why this matters: Enables service creation from environment variables.
        Setup summary: Mock UniqueSettings.from_env_auto_with_sdk_init, verify service creation.
        """
        # Arrange
        mock_settings = Mock(spec=UniqueSettings)
        mock_settings.auth.company_id.get_secret_value.return_value = "env_company"
        mock_settings.auth.user_id.get_secret_value.return_value = "env_user"
        mock_settings_class.from_env_auto_with_sdk_init.return_value = mock_settings

        # Act
        service = KnowledgeBaseService.from_settings()

        # Assert
        assert service._company_id == "env_company"
        assert service._user_id == "env_user"
        assert service._metadata_filter is None
        mock_settings_class.from_env_auto_with_sdk_init.assert_called_once()

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.UniqueSettings")
    def test_from_settings__creates_service__with_settings_filename(
        self, mock_settings_class: Mock
    ) -> None:
        """
        Purpose: Verify from_settings accepts filename parameter for settings file.
        Why this matters: Allows loading settings from specific configuration files.
        Setup summary: Mock UniqueSettings with filename, verify service creation.
        """
        # Arrange
        mock_settings = Mock(spec=UniqueSettings)
        mock_settings.auth.company_id.get_secret_value.return_value = "file_company"
        mock_settings.auth.user_id.get_secret_value.return_value = "file_user"
        mock_settings_class.from_env_auto_with_sdk_init.return_value = mock_settings

        # Act
        service = KnowledgeBaseService.from_settings(settings="test.env")

        # Assert
        assert service._company_id == "file_company"
        assert service._user_id == "file_user"
        mock_settings_class.from_env_auto_with_sdk_init.assert_called_once_with(
            filename="test.env"
        )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.UniqueSettings")
    def test_from_settings__creates_service__with_metadata_filter(
        self, mock_settings_class: Mock
    ) -> None:
        """
        Purpose: Verify from_settings accepts metadata_filter parameter.
        Why this matters: Allows setting metadata filter during service creation.
        Setup summary: Mock UniqueSettings, pass metadata_filter, verify it's stored.
        """
        # Arrange
        mock_settings = Mock(spec=UniqueSettings)
        mock_settings.auth.company_id.get_secret_value.return_value = "test_company"
        mock_settings.auth.user_id.get_secret_value.return_value = "test_user"
        mock_settings_class.from_env_auto_with_sdk_init.return_value = mock_settings

        # Act
        service = KnowledgeBaseService.from_settings(
            metadata_filter={"filter": "value"}
        )

        # Assert
        assert service._metadata_filter == {"filter": "value"}


class TestKnowledgeBaseServiceSearchContentChunks:
    """Test cases for search_content_chunks method."""

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks")
    def test_search_content_chunks__returns_chunks__with_scope_ids(
        self,
        mock_search: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify search_content_chunks returns results when scope_ids are provided.
        Why this matters: Scope-based search is a core functionality for knowledge base queries.
        Setup summary: Mock search_content_chunks function, call service method with scope_ids, assert results.
        """
        # Arrange
        mock_search.return_value = [mock_content_chunk]

        # Act
        result = base_kb_service.search_content_chunks(
            search_string="test query",
            search_type=ContentSearchType.VECTOR,
            limit=10,
            scope_ids=["scope1", "scope2"],
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == "cont_test123"
        mock_search.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            chat_id="",
            search_string="test query",
            search_type=ContentSearchType.VECTOR,
            limit=10,
            search_language="english",
            reranker_config=None,
            scope_ids=["scope1", "scope2"],
            chat_only=False,
            metadata_filter=None,
            content_ids=None,
            score_threshold=None,
        )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks")
    def test_search_content_chunks__uses_instance_metadata_filter__when_not_provided(
        self,
        mock_search: Mock,
        kb_service_with_metadata: KnowledgeBaseService,
        mock_content_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify search_content_chunks uses instance metadata_filter when parameter is None.
        Why this matters: Ensures metadata filtering works consistently across searches.
        Setup summary: Create service with metadata_filter, call search without metadata_filter param, verify instance filter used.
        """
        # Arrange
        mock_search.return_value = [mock_content_chunk]

        # Act
        result = kb_service_with_metadata.search_content_chunks(
            search_string="test",
            search_type=ContentSearchType.VECTOR,
            limit=10,
            scope_ids=["scope1"],
        )

        # Assert
        assert len(result) == 1
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["metadata_filter"] == {"key": "test_value"}

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks")
    def test_search_content_chunks__uses_provided_metadata_filter__over_instance(
        self,
        mock_search: Mock,
        kb_service_with_metadata: KnowledgeBaseService,
        mock_content_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify provided metadata_filter parameter overrides instance metadata_filter.
        Why this matters: Allows per-query metadata filtering flexibility.
        Setup summary: Create service with metadata_filter, call search with different metadata_filter, verify provided one used.
        """
        # Arrange
        mock_search.return_value = [mock_content_chunk]

        # Act
        result = kb_service_with_metadata.search_content_chunks(
            search_string="test",
            search_type=ContentSearchType.VECTOR,
            limit=10,
            scope_ids=["scope1"],
            metadata_filter={"override": "value"},
        )

        # Assert
        assert len(result) == 1
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["metadata_filter"] == {"override": "value"}

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks")
    def test_search_content_chunks__handles_error__and_reraises(
        self, mock_search: Mock, base_kb_service: KnowledgeBaseService
    ) -> None:
        """
        Purpose: Verify search_content_chunks handles exceptions and re-raises them.
        Why this matters: Error handling must preserve exception information for debugging.
        Setup summary: Mock search to raise exception, call service method, assert exception is raised.
        """
        # Arrange
        mock_search.side_effect = Exception("Search failed")

        # Act & Assert
        with pytest.raises(Exception, match="Search failed"):
            base_kb_service.search_content_chunks(
                search_string="test",
                search_type=ContentSearchType.VECTOR,
                limit=10,
                scope_ids=["scope1"],
            )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks")
    def test_search_content_chunks__with_content_ids__calls_with_correct_params(
        self,
        mock_search: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify search_content_chunks accepts content_ids parameter correctly.
        Why this matters: Content ID filtering enables targeted searches within specific documents.
        Setup summary: Mock search, call with content_ids, verify parameter passed correctly.
        """
        # Arrange
        mock_search.return_value = [mock_content_chunk]

        # Act
        result = base_kb_service.search_content_chunks(
            search_string="test",
            search_type=ContentSearchType.VECTOR,
            limit=10,
            metadata_filter={"key": "value"},
            content_ids=["cont_123", "cont_456"],
        )

        # Assert
        assert len(result) == 1
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["content_ids"] == ["cont_123", "cont_456"]

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks")
    def test_search_content_chunks__with_reranker_config__passes_config(
        self,
        mock_search: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify search_content_chunks accepts and passes reranker_config.
        Why this matters: Reranking improves search result quality.
        Setup summary: Create reranker config, call search with it, verify config passed.
        """
        # Arrange
        mock_search.return_value = [mock_content_chunk]
        reranker_config = ContentRerankerConfig(deployment_name="test_reranker")

        # Act
        result = base_kb_service.search_content_chunks(
            search_string="test",
            search_type=ContentSearchType.VECTOR,
            limit=10,
            scope_ids=["scope1"],
            reranker_config=reranker_config,
        )

        # Assert
        assert len(result) == 1
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["reranker_config"] == reranker_config

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks_async")
    async def test_search_content_chunks_async__returns_chunks__with_scope_ids(
        self,
        mock_search_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
        mock_content_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify async search_content_chunks_async returns results correctly.
        Why this matters: Async operations are essential for non-blocking I/O.
        Setup summary: Mock async search function, await service method, assert results.
        """
        # Arrange
        mock_search_async.return_value = [mock_content_chunk]

        # Act
        result = await base_kb_service.search_content_chunks_async(
            search_string="test query",
            search_type=ContentSearchType.VECTOR,
            limit=10,
            scope_ids=["scope1", "scope2"],
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == "cont_test123"
        mock_search_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks_async")
    async def test_search_content_chunks_async__uses_instance_metadata_filter(
        self,
        mock_search_async: AsyncMock,
        kb_service_with_metadata: KnowledgeBaseService,
        mock_content_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify async search uses instance metadata_filter when not provided.
        Why this matters: Consistent metadata filtering behavior across sync and async methods.
        Setup summary: Create service with metadata_filter, await async search, verify instance filter used.
        """
        # Arrange
        mock_search_async.return_value = [mock_content_chunk]

        # Act
        result = await kb_service_with_metadata.search_content_chunks_async(
            search_string="test",
            search_type=ContentSearchType.VECTOR,
            limit=10,
            scope_ids=["scope1"],
        )

        # Assert
        assert len(result) == 1
        call_kwargs = mock_search_async.call_args[1]
        assert call_kwargs["metadata_filter"] == {"key": "test_value"}

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.search_content_chunks_async")
    async def test_search_content_chunks_async__handles_error__and_reraises(
        self, mock_search_async: AsyncMock, base_kb_service: KnowledgeBaseService
    ) -> None:
        """
        Purpose: Verify async search handles exceptions and re-raises them.
        Why this matters: Error handling must work consistently in async context.
        Setup summary: Mock async search to raise exception, await service method, assert exception raised.
        """
        # Arrange
        mock_search_async.side_effect = Exception("Async search failed")

        # Act & Assert
        with pytest.raises(Exception, match="Async search failed"):
            await base_kb_service.search_content_chunks_async(
                search_string="test",
                search_type=ContentSearchType.VECTOR,
                limit=10,
                scope_ids=["scope1"],
            )


class TestKnowledgeBaseServiceSearchContents:
    """Test cases for search_contents method."""

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.search_contents")
    def test_search_contents__returns_contents__with_where_filter(
        self,
        mock_search: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content: Content,
    ) -> None:
        """
        Purpose: Verify search_contents returns Content objects matching where filter.
        Why this matters: Filter-based search is essential for querying knowledge base by metadata.
        Setup summary: Mock search_contents function, call service method with where filter, assert results.
        """
        # Arrange
        mock_search.return_value = [mock_content]

        # Act
        result = base_kb_service.search_contents(where={"key": "test_file.txt"})

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == "cont_test123"
        mock_search.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            chat_id="",
            where={"key": "test_file.txt"},
            include_failed_content=False,
        )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.search_contents")
    def test_search_contents__with_include_failed__passes_flag(
        self,
        mock_search: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content: Content,
    ) -> None:
        """
        Purpose: Verify search_contents accepts include_failed_content parameter.
        Why this matters: Allows retrieving failed content for debugging or recovery.
        Setup summary: Mock search, call with include_failed_content=True, verify flag passed.
        """
        # Arrange
        mock_search.return_value = [mock_content]

        # Act
        result = base_kb_service.search_contents(
            where={"key": "test"}, include_failed_content=True
        )

        # Assert
        assert len(result) == 1
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["include_failed_content"] is True

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.search_contents_async")
    async def test_search_contents_async__returns_contents__with_where_filter(
        self,
        mock_search_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
        mock_content: Content,
    ) -> None:
        """
        Purpose: Verify async search_contents returns Content objects correctly.
        Why this matters: Async operations enable non-blocking content searches.
        Setup summary: Mock async search function, await service method, assert results.
        """
        # Arrange
        mock_search_async.return_value = [mock_content]

        # Act
        result = await base_kb_service.search_contents_async(where={"key": "test"})

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == "cont_test123"
        mock_search_async.assert_called_once()


class TestKnowledgeBaseServiceUpload:
    """Test cases for upload methods."""

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.upload_content_from_bytes")
    def test_upload_content_from_bytes__returns_content__with_correct_params(
        self,
        mock_upload: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content: Content,
    ) -> None:
        """
        Purpose: Verify upload_content_from_bytes uploads content and returns Content object.
        Why this matters: Uploading from memory is secure and avoids disk I/O.
        Setup summary: Mock upload function, call service method with bytes, assert Content returned.
        """
        # Arrange
        mock_upload.return_value = mock_content
        content_bytes = b"test file content"

        # Act
        result = base_kb_service.upload_content_from_bytes(
            content=content_bytes,
            content_name="test.txt",
            mime_type="text/plain",
            scope_id="scope_test123",
        )

        # Assert
        assert isinstance(result, Content)
        assert result.id == "cont_test123"
        mock_upload.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            content=content_bytes,
            content_name="test.txt",
            mime_type="text/plain",
            scope_id="scope_test123",
            chat_id="",
            skip_ingestion=False,
            ingestion_config=None,
            metadata=None,
        )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.upload_content_from_bytes")
    def test_upload_content_from_bytes__with_metadata__passes_metadata(
        self,
        mock_upload: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content: Content,
    ) -> None:
        """
        Purpose: Verify upload_content_from_bytes accepts and passes metadata.
        Why this matters: Metadata enables content organization and filtering.
        Setup summary: Mock upload, call with metadata dict, verify metadata passed.
        """
        # Arrange
        mock_upload.return_value = mock_content
        metadata = {"category": "test", "version": "1.0"}

        # Act
        result = base_kb_service.upload_content_from_bytes(
            content=b"test",
            content_name="test.txt",
            mime_type="text/plain",
            scope_id="scope_test123",
            metadata=metadata,
        )

        # Assert
        assert isinstance(result, Content)
        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["metadata"] == metadata

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.upload_content_from_bytes_async")
    async def test_upload_content_from_bytes_async__returns_content(
        self,
        mock_upload_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
        mock_content: Content,
    ) -> None:
        """
        Purpose: Verify async upload_content_from_bytes_async uploads and returns Content.
        Why this matters: Async uploads enable non-blocking file operations.
        Setup summary: Mock async upload function, await service method, assert Content returned.
        """
        # Arrange
        mock_upload_async.return_value = mock_content

        # Act
        result = await base_kb_service.upload_content_from_bytes_async(
            content=b"test",
            content_name="test.txt",
            mime_type="text/plain",
            scope_id="scope_test123",
        )

        # Assert
        assert isinstance(result, Content)
        assert result.id == "cont_test123"
        mock_upload_async.assert_called_once()

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.upload_content")
    def test_upload_content__returns_content__from_file_path(
        self,
        mock_upload: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content: Content,
        tmp_path: Path,
    ) -> None:
        """
        Purpose: Verify upload_content uploads file from path and returns Content.
        Why this matters: File-based uploads are common for bulk operations.
        Setup summary: Create temp file, mock upload function, call service method, assert Content returned.
        """
        # Arrange
        mock_upload.return_value = mock_content
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Act
        result = base_kb_service.upload_content(
            path_to_content=str(test_file),
            content_name="test.txt",
            mime_type="text/plain",
            scope_id="scope_test123",
        )

        # Assert
        assert isinstance(result, Content)
        assert result.id == "cont_test123"
        mock_upload.assert_called_once()


class TestKnowledgeBaseServiceDownload:
    """Test cases for download methods."""

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.download_content_to_file_by_id")
    def test_download_content_to_file__returns_path__with_content_id(
        self,
        mock_download: Mock,
        base_kb_service: KnowledgeBaseService,
        tmp_path: Path,
    ) -> None:
        """
        Purpose: Verify download_content_to_file downloads content and returns file path.
        Why this matters: File downloads enable local content access.
        Setup summary: Mock download function to return path, call service method, assert path returned.
        """
        # Arrange
        expected_path = tmp_path / "downloaded.txt"
        mock_download.return_value = expected_path

        # Act
        result = base_kb_service.download_content_to_file(
            content_id="cont_test123",
            output_dir_path=tmp_path,
            output_filename="downloaded.txt",
        )

        # Assert
        assert result == expected_path
        mock_download.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            content_id="cont_test123",
            chat_id="",
            filename="downloaded.txt",
            tmp_dir_path=tmp_path,
        )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.download_content_to_bytes")
    def test_download_content_to_bytes__returns_bytes__with_content_id(
        self,
        mock_download: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify download_content_to_bytes downloads content to memory.
        Why this matters: Memory-based downloads avoid disk I/O for in-memory processing.
        Setup summary: Mock download function to return bytes, call service method, assert bytes returned.
        """
        # Arrange
        expected_bytes = b"test file content"
        mock_download.return_value = expected_bytes

        # Act
        result = base_kb_service.download_content_to_bytes(content_id="cont_test123")

        # Assert
        assert isinstance(result, bytes)
        assert result == expected_bytes
        mock_download.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            content_id="cont_test123",
            chat_id=None,
        )


class TestKnowledgeBaseServiceBatchUpload:
    """Test cases for batch_file_upload method."""

    @pytest.mark.ai
    def test_batch_file_upload__raises_error__when_file_folder_mismatch(
        self, base_kb_service: KnowledgeBaseService, tmp_path: Path
    ) -> None:
        """
        Purpose: Verify batch_file_upload raises ValueError when file and folder counts don't match.
        Why this matters: Prevents data loss from mismatched upload configurations.
        Setup summary: Create mismatched file and folder lists, call batch_file_upload, assert ValueError.
        """
        # Arrange
        local_files = [tmp_path / "file1.txt", tmp_path / "file2.txt"]
        remote_folders = [PurePath("/folder1")]

        # Act & Assert
        with pytest.raises(
            ValueError, match="number of local files and remote folders"
        ):
            base_kb_service.batch_file_upload(
                local_files=local_files, remote_folders=remote_folders
            )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.mimetypes.guess_type")
    @patch.object(KnowledgeBaseService, "create_folders")
    @patch.object(KnowledgeBaseService, "get_file_names_in_folder")
    @patch.object(KnowledgeBaseService, "upload_content")
    def test_batch_file_upload__uploads_files__to_correct_folders(
        self,
        mock_upload: Mock,
        mock_get_names: Mock,
        mock_create_folders: Mock,
        mock_guess_type: Mock,
        base_kb_service: KnowledgeBaseService,
        tmp_path: Path,
    ) -> None:
        """
        Purpose: Verify batch_file_upload creates folders and uploads files correctly.
        Why this matters: Batch operations enable efficient bulk content management.
        Setup summary: Mock folder creation and upload, create test files, call batch_file_upload, verify calls.
        """
        # Arrange
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1")
        file2 = tmp_path / "file2.txt"
        file2.write_text("content2")

        mock_create_folders.return_value = [
            BaseFolderInfo(id="scope1", name="folder1", parent_id=None),
            BaseFolderInfo(id="scope2", name="folder2", parent_id=None),
        ]
        mock_get_names.return_value = []
        mock_guess_type.return_value = ("text/plain", None)
        mock_upload.return_value = None

        # Act
        base_kb_service.batch_file_upload(
            local_files=[file1, file2],
            remote_folders=[PurePath("/folder1"), PurePath("/folder2")],
        )

        # Assert
        assert mock_create_folders.call_count == 1
        assert mock_upload.call_count == 2

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.mimetypes.guess_type")
    @patch.object(KnowledgeBaseService, "create_folders")
    @patch.object(KnowledgeBaseService, "get_file_names_in_folder")
    @patch.object(KnowledgeBaseService, "upload_content")
    def test_batch_file_upload__skips_existing_files__when_overwrite_false(
        self,
        mock_upload: Mock,
        mock_get_names: Mock,
        mock_create_folders: Mock,
        mock_guess_type: Mock,
        base_kb_service: KnowledgeBaseService,
        tmp_path: Path,
    ) -> None:
        """
        Purpose: Verify batch_file_upload skips existing files when overwrite is False.
        Why this matters: Prevents accidental overwrites of existing content.
        Setup summary: Mock get_file_names_in_folder to return existing file, call batch_file_upload, verify upload not called.
        """
        # Arrange
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1")

        mock_create_folders.return_value = [
            BaseFolderInfo(id="scope1", name="folder1", parent_id=None)
        ]
        mock_get_names.return_value = ["file1.txt"]
        mock_guess_type.return_value = ("text/plain", None)

        # Act
        base_kb_service.batch_file_upload(
            local_files=[file1],
            remote_folders=[PurePath("/folder1")],
            overwrite=False,
        )

        # Assert
        mock_upload.assert_not_called()

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.mimetypes.guess_type")
    @patch.object(KnowledgeBaseService, "create_folders")
    @patch.object(KnowledgeBaseService, "get_file_names_in_folder")
    @patch.object(KnowledgeBaseService, "upload_content")
    def test_batch_file_upload__uses_metadata_generator__when_provided(
        self,
        mock_upload: Mock,
        mock_get_names: Mock,
        mock_create_folders: Mock,
        mock_guess_type: Mock,
        base_kb_service: KnowledgeBaseService,
        tmp_path: Path,
    ) -> None:
        """
        Purpose: Verify batch_file_upload uses metadata_generator function when provided.
        Why this matters: Enables dynamic metadata generation per file during batch uploads.
        Setup summary: Create metadata generator function, call batch_file_upload, verify metadata passed to upload.
        """
        # Arrange
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1")

        def metadata_gen(local_path: Path, remote_path: PurePath) -> dict[str, Any]:
            return {"source": str(local_path), "folder": str(remote_path)}

        mock_create_folders.return_value = [
            BaseFolderInfo(id="scope1", name="folder1", parent_id=None)
        ]
        mock_get_names.return_value = []
        mock_guess_type.return_value = ("text/plain", None)
        mock_upload.return_value = None

        # Act
        base_kb_service.batch_file_upload(
            local_files=[file1],
            remote_folders=[PurePath("/folder1")],
            metadata_generator=metadata_gen,
        )

        # Assert
        mock_upload.assert_called_once()
        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["metadata"] == {
            "source": str(file1),
            "folder": "/folder1",
        }

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.mimetypes.guess_type")
    @patch.object(KnowledgeBaseService, "create_folders")
    @patch.object(KnowledgeBaseService, "get_file_names_in_folder")
    @patch.object(KnowledgeBaseService, "upload_content")
    def test_batch_file_upload__skips_file__when_mime_type_none(
        self,
        mock_upload: Mock,
        mock_get_names: Mock,
        mock_create_folders: Mock,
        mock_guess_type: Mock,
        base_kb_service: KnowledgeBaseService,
        tmp_path: Path,
    ) -> None:
        """
        Purpose: Verify batch_file_upload skips files when mime type cannot be determined.
        Why this matters: Prevents upload errors from unsupported file types.
        Setup summary: Mock guess_type to return None, call batch_file_upload, verify file skipped.
        """
        # Arrange
        file1 = tmp_path / "file1.unknown"
        file1.write_text("content1")

        mock_create_folders.return_value = [
            BaseFolderInfo(id="scope1", name="folder1", parent_id=None)
        ]
        mock_get_names.return_value = []
        mock_guess_type.return_value = (None, None)
        mock_upload.return_value = None

        # Act
        base_kb_service.batch_file_upload(
            local_files=[file1],
            remote_folders=[PurePath("/folder1")],
        )

        # Assert
        # No upload should occur since mime type is None
        mock_upload.assert_not_called()


class TestKnowledgeBaseServiceContentInfo:
    """Test cases for content info methods."""

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.get_content_info")
    def test_get_paginated_content_infos__returns_paginated_results(
        self,
        mock_get_info: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content_info: ContentInfo,
    ) -> None:
        """
        Purpose: Verify get_paginated_content_infos returns paginated content information.
        Why this matters: Pagination enables efficient retrieval of large content lists.
        Setup summary: Mock get_content_info to return paginated results, call service method, assert results.
        """
        # Arrange
        mock_get_info.return_value = PaginatedContentInfos(
            object="list",
            content_infos=[mock_content_info],
            total_count=1,
        )

        # Act
        result = base_kb_service.get_paginated_content_infos()

        # Assert
        assert isinstance(result, PaginatedContentInfos)
        assert len(result.content_infos) == 1
        assert result.content_infos[0].id == "cont_test123"
        mock_get_info.assert_called_once()

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.get_content_info")
    def test_get_paginated_content_infos__with_metadata_filter__passes_filter(
        self,
        mock_get_info: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_paginated_content_infos accepts and passes metadata_filter.
        Why this matters: Metadata filtering enables scoped content queries.
        Setup summary: Mock get_content_info, call with metadata_filter, verify filter passed.
        """
        # Arrange
        mock_get_info.return_value = PaginatedContentInfos(
            object="list", content_infos=[], total_count=0
        )
        metadata_filter = {"key": "value"}

        # Act
        base_kb_service.get_paginated_content_infos(metadata_filter=metadata_filter)

        # Assert
        call_kwargs = mock_get_info.call_args[1]
        assert call_kwargs["metadata_filter"] == metadata_filter

    @pytest.mark.ai
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos")
    def test_get_file_names_in_folder__returns_file_names__for_scope_id(
        self,
        mock_get_paginated: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content_info: ContentInfo,
    ) -> None:
        """
        Purpose: Verify get_file_names_in_folder returns list of file names in folder.
        Why this matters: Enables listing folder contents for navigation and management.
        Setup summary: Mock get_paginated_content_infos, call get_file_names_in_folder, assert file names returned.
        """
        # Arrange
        mock_get_paginated.return_value = PaginatedContentInfos(
            object="list",
            content_infos=[mock_content_info],
            total_count=1,
        )

        # Act
        result = base_kb_service.get_file_names_in_folder(scope_id="scope_test123")

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "test_file.txt"


class TestKnowledgeBaseServiceFolderManagement:
    """Test cases for folder management methods."""

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.get_folder_info")
    def test_get_folder_info__returns_folder_info__for_scope_id(
        self,
        mock_get_folder: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_folder_info: FolderInfo,
    ) -> None:
        """
        Purpose: Verify get_folder_info returns FolderInfo for given scope_id.
        Why this matters: Folder information is needed for navigation and path resolution.
        Setup summary: Mock get_folder_info, call service method, assert FolderInfo returned.
        """
        # Arrange
        mock_get_folder.return_value = mock_folder_info

        # Act
        result = base_kb_service.get_folder_info(scope_id="scope_test123")

        # Assert
        assert isinstance(result, FolderInfo)
        assert result.id == "scope_test123"
        assert result.name == "test_folder"
        mock_get_folder.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            scope_id="scope_test123",
        )

    @pytest.mark.ai
    @patch.object(unique_sdk.Folder, "create_paths")
    def test_create_folders__returns_folder_infos__for_paths(
        self,
        mock_create_paths: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify create_folders creates folders and returns BaseFolderInfo list.
        Why this matters: Folder creation is essential for organizing knowledge base content.
        Setup summary: Mock Folder.create_paths, call create_folders, assert BaseFolderInfo list returned.
        """
        # Arrange
        mock_create_paths.return_value = {
            "createdFolders": [
                {"id": "scope1", "name": "folder1", "parentId": None},
                {"id": "scope2", "name": "folder2", "parentId": "scope1"},
            ]
        }

        # Act
        result = base_kb_service.create_folders(
            paths=[PurePath("/folder1"), PurePath("/folder1/folder2")]
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(folder, BaseFolderInfo) for folder in result)
        assert result[0].id == "scope1"
        assert result[1].id == "scope2"
        mock_create_paths.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            paths=["/folder1", "/folder1/folder2"],
        )

    @pytest.mark.ai
    @patch.object(KnowledgeBaseService, "get_folder_info")
    def test_get_folder_path__returns_path__for_scope_id(
        self,
        mock_get_folder: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_folder_path returns PurePath for given scope_id.
        Why this matters: Path resolution enables folder navigation and display.
        Setup summary: Mock get_folder_info with parent hierarchy, call get_folder_path, assert path returned.
        """
        # Arrange
        root_folder = FolderInfo(
            id="scope_root",
            name="root",
            parent_id=None,
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )
        child_folder = FolderInfo(
            id="scope_child",
            name="child",
            parent_id="scope_root",
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )

        def folder_info_side_effect(scope_id: str) -> FolderInfo:
            if scope_id == "scope_child":
                return child_folder
            return root_folder

        mock_get_folder.side_effect = folder_info_side_effect

        # Act
        result = base_kb_service.get_folder_path(scope_id="scope_child")

        # Assert
        assert isinstance(result, PurePath)
        # Note: The actual path depends on _get_knowledge_base_location implementation

    @pytest.mark.ai
    @patch.object(KnowledgeBaseService, "get_folder_info")
    def test_get_scope_id_path__returns_scope_ids__for_scope_id(
        self,
        mock_get_folder: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_scope_id_path returns list of scope IDs from root to folder.
        Why this matters: Scope ID paths enable hierarchical folder navigation.
        Setup summary: Mock get_folder_info with parent hierarchy, call get_scope_id_path, assert scope ID list returned.
        """
        # Arrange
        root_folder = FolderInfo(
            id="scope_root",
            name="root",
            parent_id=None,
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )
        child_folder = FolderInfo(
            id="scope_child",
            name="child",
            parent_id="scope_root",
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )

        def folder_info_side_effect(scope_id: str) -> FolderInfo:
            if scope_id == "scope_child":
                return child_folder
            return root_folder

        mock_get_folder.side_effect = folder_info_side_effect

        # Act
        result = base_kb_service.get_scope_id_path(scope_id="scope_child")

        # Assert
        assert isinstance(result, list)
        assert all(isinstance(scope_id, str) for scope_id in result)


class TestKnowledgeBaseServiceMetadata:
    """Test cases for metadata management methods."""

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.update_content")
    def test_replace_content_metadata__replaces_all_metadata(
        self,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
        mock_content_info: ContentInfo,
    ) -> None:
        """
        Purpose: Verify replace_content_metadata replaces all metadata for content.
        Why this matters: Complete metadata replacement enables content re-tagging.
        Setup summary: Mock update_content, call replace_content_metadata, verify metadata replaced.
        """
        # Arrange
        new_metadata = {"new_key": "new_value"}
        mock_update.return_value = mock_content_info

        # Act
        result = base_kb_service.replace_content_metadata(
            content_id="cont_test123", metadata=new_metadata
        )

        # Assert
        assert isinstance(result, ContentInfo)
        mock_update.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            content_id="cont_test123",
            metadata=new_metadata,
        )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.update_content")
    def test_update_content_metadata__merges_metadata__with_existing(
        self,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify update_content_metadata merges additional metadata with existing.
        Why this matters: Incremental metadata updates preserve existing tags.
        Setup summary: Create ContentInfo with existing metadata, call update_content_metadata, verify merge.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="test.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"existing": "value"},
        )
        mock_update.return_value = content_info

        # Act
        result = base_kb_service.update_content_metadata(
            content_info=content_info, additional_metadata={"new_key": "new_value"}
        )

        # Assert
        assert isinstance(result, ContentInfo)
        # Verify that metadata was merged (camelized and forbidden keys removed)
        call_kwargs = mock_update.call_args[1]
        assert "metadata" in call_kwargs

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.update_content")
    def test_update_content_metadata__creates_metadata__when_none(
        self,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify update_content_metadata creates metadata when content has none.
        Why this matters: Enables adding metadata to content that previously had none.
        Setup summary: Create ContentInfo without metadata, call update_content_metadata, verify metadata created.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="test.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata=None,
        )
        mock_update.return_value = content_info

        # Act
        result = base_kb_service.update_content_metadata(
            content_info=content_info, additional_metadata={"new_key": "new_value"}
        )

        # Assert
        assert isinstance(result, ContentInfo)
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["metadata"] is not None

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.update_content")
    def test_remove_content_metadata__removes_keys__from_metadata(
        self,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify remove_content_metadata removes specified keys from metadata.
        Why this matters: Enables cleanup of obsolete or incorrect metadata.
        Setup summary: Create ContentInfo with metadata, call remove_content_metadata, verify keys removed.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="test.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"key1": "value1", "key2": "value2"},
        )
        mock_update.return_value = content_info

        # Act
        result = base_kb_service.remove_content_metadata(
            content_info=content_info, keys_to_remove=["key1"]
        )

        # Assert
        assert isinstance(result, ContentInfo)
        call_kwargs = mock_update.call_args[1]
        # Verify that key1 was set to None in metadata
        assert call_kwargs["metadata"] is not None

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.update_content")
    def test_remove_content_metadata__handles_none_metadata__gracefully(
        self,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify remove_content_metadata handles content with None metadata gracefully.
        Why this matters: Prevents errors when removing metadata from content without metadata.
        Setup summary: Create ContentInfo with None metadata, call remove_content_metadata, verify no error.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="test.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata=None,
        )

        # Act
        result = base_kb_service.remove_content_metadata(
            content_info=content_info, keys_to_remove=["key1"]
        )

        # Assert
        assert result == content_info
        mock_update.assert_not_called()

    @pytest.mark.ai
    @patch.object(KnowledgeBaseService, "update_content_metadata")
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos")
    def test_update_contents_metadata__updates_multiple__with_metadata_filter(
        self,
        mock_get_paginated: Mock,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify update_contents_metadata updates multiple contents using metadata_filter.
        Why this matters: Enables bulk metadata updates for filtered content sets.
        Setup summary: Mock get_paginated_content_infos to return multiple ContentInfos, call update_contents_metadata, verify all updated.
        """
        # Arrange
        content_info1 = ContentInfo(
            id="cont_test1",
            object="content",
            key="test1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        content_info2 = ContentInfo(
            id="cont_test2",
            object="content",
            key="test2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        mock_get_paginated.return_value = PaginatedContentInfos(
            object="list",
            content_infos=[content_info1, content_info2],
            total_count=2,
        )
        mock_update.return_value = content_info1

        # Act
        result = base_kb_service.update_contents_metadata(
            additional_metadata={"new_key": "new_value"},
            metadata_filter={"key": "test"},
        )

        # Assert
        assert len(result) == 2
        assert mock_update.call_count == 2

    @pytest.mark.ai
    @patch.object(KnowledgeBaseService, "remove_content_metadata")
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos")
    def test_remove_contents_metadata__removes_keys__from_multiple(
        self,
        mock_get_paginated: Mock,
        mock_remove: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify remove_contents_metadata removes keys from multiple contents.
        Why this matters: Enables bulk metadata cleanup operations.
        Setup summary: Mock get_paginated_content_infos to return multiple ContentInfos, call remove_contents_metadata, verify all processed.
        """
        # Arrange
        content_info1 = ContentInfo(
            id="cont_test1",
            object="content",
            key="test1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        content_info2 = ContentInfo(
            id="cont_test2",
            object="content",
            key="test2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        mock_get_paginated.return_value = PaginatedContentInfos(
            object="list",
            content_infos=[content_info1, content_info2],
            total_count=2,
        )
        mock_remove.return_value = content_info1

        # Act
        result = base_kb_service.remove_contents_metadata(
            keys_to_remove=["key1"], metadata_filter={"key": "test"}
        )

        # Assert
        assert len(result) == 2
        assert mock_remove.call_count == 2


class TestKnowledgeBaseServiceDelete:
    """Test cases for delete methods."""

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.delete_content")
    def test_delete_content__by_id__returns_response(
        self,
        mock_delete: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify delete_content deletes content by ID and returns response.
        Why this matters: Content deletion is essential for knowledge base management.
        Setup summary: Mock delete_content function, call service method with content_id, assert response returned.
        """
        # Arrange
        mock_delete.return_value = DeleteContentResponse(
            content_id="cont_test123", object="content"
        )

        # Act
        result = base_kb_service.delete_content(content_id="cont_test123")

        # Assert
        assert isinstance(result, DeleteContentResponse)
        assert result.content_id == "cont_test123"
        mock_delete.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            content_id="cont_test123",
            file_path=None,
        )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.delete_content")
    def test_delete_content__by_file_path__returns_response(
        self,
        mock_delete: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify delete_content deletes content by file path and returns response.
        Why this matters: File path-based deletion enables bulk operations.
        Setup summary: Mock delete_content function, call service method with file_path, assert response returned.
        """
        # Arrange
        mock_delete.return_value = DeleteContentResponse(
            content_id="cont_test123", object="content"
        )

        # Act
        result = base_kb_service.delete_content(file_path="/path/to/file.txt")

        # Assert
        assert isinstance(result, DeleteContentResponse)
        mock_delete.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            content_id=None,
            file_path="/path/to/file.txt",
        )

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.delete_content")
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos")
    def test_delete_contents__deletes_all__matching_metadata_filter(
        self,
        mock_get_paginated: Mock,
        mock_delete: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify delete_contents deletes all content matching metadata filter.
        Why this matters: Enables bulk deletion operations for filtered content sets.
        Setup summary: Mock get_paginated_content_infos to return multiple ContentInfos, call delete_contents, verify all deleted.
        """
        # Arrange
        content_info1 = ContentInfo(
            id="cont_test1",
            object="content",
            key="test1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        content_info2 = ContentInfo(
            id="cont_test2",
            object="content",
            key="test2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        mock_get_paginated.return_value = PaginatedContentInfos(
            object="list",
            content_infos=[content_info1, content_info2],
            total_count=2,
        )
        mock_delete.return_value = DeleteContentResponse(
            content_id="cont_test1", object="content"
        )

        # Act
        result = base_kb_service.delete_contents(metadata_filter={"key": "test"})

        # Assert
        assert len(result) == 2
        assert mock_delete.call_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.delete_content_async")
    async def test_delete_content_async__by_id__returns_response(
        self,
        mock_delete_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify async delete_content_async deletes content by ID.
        Why this matters: Async deletion enables non-blocking content removal.
        Setup summary: Mock async delete function, await service method, assert response returned.
        """
        # Arrange
        mock_delete_async.return_value = DeleteContentResponse(
            content_id="cont_test123", object="content"
        )

        # Act
        result = await base_kb_service.delete_content_async(content_id="cont_test123")

        # Assert
        assert isinstance(result, DeleteContentResponse)
        assert result.content_id == "cont_test123"
        mock_delete_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.delete_content_async")
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos")
    async def test_delete_contents_async__deletes_all__concurrently(
        self,
        mock_get_paginated: Mock,
        mock_delete_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify async delete_contents_async deletes multiple contents concurrently.
        Why this matters: Concurrent deletion improves performance for bulk operations.
        Setup summary: Mock get_paginated_content_infos and async delete, await delete_contents_async, verify concurrent execution.
        """
        # Arrange
        content_info1 = ContentInfo(
            id="cont_test1",
            object="content",
            key="test1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        content_info2 = ContentInfo(
            id="cont_test2",
            object="content",
            key="test2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        mock_get_paginated.return_value = PaginatedContentInfos(
            object="list",
            content_infos=[content_info1, content_info2],
            total_count=2,
        )
        mock_delete_async.return_value = DeleteContentResponse(
            content_id="cont_test1", object="content"
        )

        # Act
        result = await base_kb_service.delete_contents_async(
            metadata_filter={"key": "test"}
        )

        # Assert
        assert len(result) == 2
        assert mock_delete_async.call_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos")
    async def test_delete_contents_async__returns_empty__when_no_filter(
        self,
        mock_get_paginated: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify delete_contents_async returns empty list when metadata_filter is empty.
        Why this matters: Prevents accidental deletion when no filter is provided.
        Setup summary: Call delete_contents_async with empty filter, assert empty list returned.
        """
        # Act
        result = await base_kb_service.delete_contents_async(metadata_filter={})

        # Assert
        assert result == []
        mock_get_paginated.assert_not_called()


class TestKnowledgeBaseServiceEdgeCases:
    """Test cases for edge cases and private method behaviors."""

    @pytest.mark.ai
    @patch.object(KnowledgeBaseService, "get_folder_info")
    def test_get_folder_path__handles_root_folder__with_no_parent(
        self,
        mock_get_folder: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_folder_path handles root folder with no parent correctly.
        Why this matters: Root folders have special path handling that must work correctly.
        Setup summary: Mock get_folder_info to return root folder (parent_id=None), call get_folder_path, assert path starts with /.
        """
        # Arrange
        root_folder = FolderInfo(
            id="scope_root",
            name="root",
            parent_id=None,
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )
        mock_get_folder.return_value = root_folder

        # Act
        result = base_kb_service.get_folder_path(scope_id="scope_root")

        # Assert
        assert isinstance(result, PurePath)
        # Root folder path should start with /
        assert str(result).startswith("/")

    @pytest.mark.ai
    @patch.object(KnowledgeBaseService, "get_folder_info")
    def test_get_scope_id_path__handles_single_level_folder(
        self,
        mock_get_folder: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_scope_id_path handles single-level folder correctly.
        Why this matters: Single-level folders are common and must be handled correctly.
        Setup summary: Mock get_folder_info to return folder with no parent, call get_scope_id_path, assert single scope ID returned.
        """
        # Arrange
        root_folder = FolderInfo(
            id="scope_root",
            name="root",
            parent_id=None,
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )
        mock_get_folder.return_value = root_folder

        # Act
        result = base_kb_service.get_scope_id_path(scope_id="scope_root")

        # Assert
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "scope_root" in result

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.update_content")
    def test_update_content_metadata__removes_forbidden_keys(
        self,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify update_content_metadata removes forbidden metadata keys.
        Why this matters: Prevents overwriting system-managed metadata fields.
        Setup summary: Create ContentInfo, call update_content_metadata with forbidden keys, verify keys removed.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="test.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={},
        )
        mock_update.return_value = content_info

        # Act
        base_kb_service.update_content_metadata(
            content_info=content_info,
            additional_metadata={
                "key": "should_be_removed",
                "url": "should_be_removed",
                "title": "should_be_removed",
                "folderId": "should_be_removed",
                "valid_key": "should_remain",
            },
        )

        # Assert
        call_kwargs = mock_update.call_args[1]
        metadata = call_kwargs["metadata"]
        # Verify forbidden keys are not in metadata
        assert "key" not in metadata or metadata.get("key") is None
        assert "valid_key" in metadata or "validKey" in metadata

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.update_content")
    def test_update_contents_metadata__with_content_infos__updates_directly(
        self,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify update_contents_metadata updates provided content_infos directly.
        Why this matters: Enables updating specific content without querying.
        Setup summary: Provide content_infos list, call update_contents_metadata, verify all updated without querying.
        """
        # Arrange
        content_info1 = ContentInfo(
            id="cont_test1",
            object="content",
            key="test1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        content_info2 = ContentInfo(
            id="cont_test2",
            object="content",
            key="test2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        mock_update.return_value = content_info1

        # Act
        result = base_kb_service.update_contents_metadata(
            additional_metadata={"new_key": "new_value"},
            content_infos=[content_info1, content_info2],
        )

        # Assert
        assert len(result) == 2
        assert mock_update.call_count == 2

    @pytest.mark.ai
    @patch("unique_toolkit.services.knowledge_base.update_content")
    def test_remove_contents_metadata__with_content_infos__removes_directly(
        self,
        mock_update: Mock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify remove_contents_metadata removes keys from provided content_infos.
        Why this matters: Enables removing metadata from specific content without querying.
        Setup summary: Provide content_infos list, call remove_contents_metadata, verify all processed.
        """
        # Arrange
        content_info1 = ContentInfo(
            id="cont_test1",
            object="content",
            key="test1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"key1": "value1"},
        )
        content_info2 = ContentInfo(
            id="cont_test2",
            object="content",
            key="test2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"key1": "value1"},
        )

        mock_update.return_value = content_info1

        # Act
        result = base_kb_service.remove_contents_metadata(
            keys_to_remove=["key1"],
            content_infos=[content_info1, content_info2],
        )

        # Assert
        assert len(result) == 2
        assert mock_update.call_count == 2


class TestExtractFolderMetadataFromContentInfos:
    """Test cases for extract_folder_metadata_from_content_infos static method."""

    @pytest.mark.ai
    def test_extract_folder_metadata__returns_scope_ids__from_folder_id_path(
        self,
    ) -> None:
        """
        Purpose: Verify extract_folder_metadata_from_content_infos extracts scope IDs from folderIdPath.
        Why this matters: Scope IDs are needed to translate to folder names via API.
        Setup summary: Create ContentInfo with folderIdPath, call method, verify scope IDs extracted.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="test.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1/scope2/scope3"},
        )

        # Act
        scope_ids, folder_id_paths, known_folder_paths = (
            KnowledgeBaseService.extract_folder_metadata_from_content_infos(
                [content_info]
            )
        )

        # Assert
        assert scope_ids == {"scope1", "scope2", "scope3"}
        assert folder_id_paths == {"uniquepathid://scope1/scope2/scope3"}
        assert known_folder_paths == set()

    @pytest.mark.ai
    def test_extract_folder_metadata__returns_known_paths__from_full_path(
        self,
    ) -> None:
        """
        Purpose: Verify extract_folder_metadata_from_content_infos extracts known paths from {FullPath}.
        Why this matters: {FullPath} metadata contains already resolved paths that don't need translation.
        Setup summary: Create ContentInfo with {FullPath}, call method, verify known paths extracted.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="test.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={r"{FullPath}": "/Documents/Reports"},
        )

        # Act
        scope_ids, folder_id_paths, known_folder_paths = (
            KnowledgeBaseService.extract_folder_metadata_from_content_infos(
                [content_info]
            )
        )

        # Assert
        assert scope_ids == set()
        assert folder_id_paths == set()
        assert known_folder_paths == {"/Documents/Reports"}

    @pytest.mark.ai
    def test_extract_folder_metadata__handles_mixed_content(
        self,
    ) -> None:
        """
        Purpose: Verify extract_folder_metadata_from_content_infos handles content with different metadata types.
        Why this matters: Real knowledge bases contain content with different metadata formats.
        Setup summary: Create multiple ContentInfos with different metadata, verify all extracted correctly.
        """
        # Arrange
        content_with_folder_id = ContentInfo(
            id="cont_1",
            object="content",
            key="file1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1/scope2"},
        )
        content_with_full_path = ContentInfo(
            id="cont_2",
            object="content",
            key="file2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={r"{FullPath}": "/Shared/Data"},
        )
        content_without_metadata = ContentInfo(
            id="cont_3",
            object="content",
            key="file3.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata=None,
        )

        # Act
        scope_ids, folder_id_paths, known_folder_paths = (
            KnowledgeBaseService.extract_folder_metadata_from_content_infos(
                [
                    content_with_folder_id,
                    content_with_full_path,
                    content_without_metadata,
                ]
            )
        )

        # Assert
        assert scope_ids == {"scope1", "scope2"}
        assert folder_id_paths == {"uniquepathid://scope1/scope2"}
        assert known_folder_paths == {"/Shared/Data"}

    @pytest.mark.ai
    def test_extract_folder_metadata__handles_empty_list(
        self,
    ) -> None:
        """
        Purpose: Verify extract_folder_metadata_from_content_infos handles empty input.
        Why this matters: Edge case when no content exists.
        Setup summary: Call with empty list, verify empty sets returned.
        """
        # Act
        scope_ids, folder_id_paths, known_folder_paths = (
            KnowledgeBaseService.extract_folder_metadata_from_content_infos([])
        )

        # Assert
        assert scope_ids == set()
        assert folder_id_paths == set()
        assert known_folder_paths == set()

    @pytest.mark.ai
    def test_extract_folder_metadata__deduplicates_scope_ids(
        self,
    ) -> None:
        """
        Purpose: Verify extract_folder_metadata_from_content_infos deduplicates scope IDs.
        Why this matters: Multiple files can share folders, scope IDs should be unique.
        Setup summary: Create ContentInfos with overlapping scope IDs, verify deduplication.
        """
        # Arrange
        content_1 = ContentInfo(
            id="cont_1",
            object="content",
            key="file1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1/scope2"},
        )
        content_2 = ContentInfo(
            id="cont_2",
            object="content",
            key="file2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1/scope3"},
        )

        # Act
        scope_ids, folder_id_paths, known_folder_paths = (
            KnowledgeBaseService.extract_folder_metadata_from_content_infos(
                [content_1, content_2]
            )
        )

        # Assert
        assert scope_ids == {"scope1", "scope2", "scope3"}
        assert len(folder_id_paths) == 2

    @pytest.mark.ai
    def test_extract_folder_metadata__handles_content_with_empty_metadata(
        self,
    ) -> None:
        """
        Purpose: Verify extract_folder_metadata_from_content_infos handles content with empty metadata dict.
        Why this matters: Content may have empty metadata dict rather than None.
        Setup summary: Create ContentInfo with empty metadata dict, verify no errors.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="test.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={},
        )

        # Act
        scope_ids, folder_id_paths, known_folder_paths = (
            KnowledgeBaseService.extract_folder_metadata_from_content_infos(
                [content_info]
            )
        )

        # Assert
        assert scope_ids == set()
        assert folder_id_paths == set()
        assert known_folder_paths == set()


class TestTranslateScopeIdsToFolderNameAsync:
    """Test cases for _translate_scope_ids_to_folder_name_async method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_folder_info_async")
    async def test_translate_scope_ids__returns_mapping__for_scope_ids(
        self,
        mock_get_folder_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify _translate_scope_ids_to_folder_name_async returns correct mapping.
        Why this matters: Enables translating internal scope IDs to human-readable folder names.
        Setup summary: Mock folder info responses, call method with scope IDs, verify mapping.
        """
        # Arrange
        folder1 = FolderInfo(
            id="scope1",
            name="Documents",
            parent_id=None,
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )
        folder2 = FolderInfo(
            id="scope2",
            name="Reports",
            parent_id="scope1",
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )

        async def folder_info_side_effect(scope_id: str) -> FolderInfo:
            if scope_id == "scope1":
                return folder1
            return folder2

        mock_get_folder_async.side_effect = folder_info_side_effect

        # Act
        result = await base_kb_service._translate_scope_ids_to_folder_name_async(
            {"scope1", "scope2"}
        )

        # Assert
        assert result == {"scope1": "Documents", "scope2": "Reports"}
        assert mock_get_folder_async.call_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_folder_info_async")
    async def test_translate_scope_ids__handles_empty_set(
        self,
        mock_get_folder_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify _translate_scope_ids_to_folder_name_async handles empty input.
        Why this matters: Edge case when no scope IDs need translation.
        Setup summary: Call with empty set, verify empty dict returned.
        """
        # Act
        result = await base_kb_service._translate_scope_ids_to_folder_name_async(set())

        # Assert
        assert result == {}
        mock_get_folder_async.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_folder_info_async")
    async def test_translate_scope_ids__calls_concurrently(
        self,
        mock_get_folder_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify _translate_scope_ids_to_folder_name_async makes concurrent API calls.
        Why this matters: Concurrent translation improves performance for many scope IDs.
        Setup summary: Mock multiple folder infos, call method, verify all called.
        """
        # Arrange
        import time

        folders = {
            f"scope{i}": FolderInfo(
                id=f"scope{i}",
                name=f"Folder{i}",
                parent_id=None,
                ingestion_config={},
                created_at=None,
                updated_at=None,
                external_id=None,
            )
            for i in range(5)
        }

        async def folder_info_side_effect(scope_id: str) -> FolderInfo:
            return folders[scope_id]

        mock_get_folder_async.side_effect = folder_info_side_effect

        # Act
        start_time = time.perf_counter()
        result = await base_kb_service._translate_scope_ids_to_folder_name_async(
            set(folders.keys())
        )
        duration = time.perf_counter() - start_time

        # Assert
        assert len(result) == 5
        assert mock_get_folder_async.call_count == 5
        # Duration should be minimal since calls are concurrent (mocked)
        assert duration < 1.0  # Should complete quickly with mocks


class TestGetContentInfosAsync:
    """Test cases for get_content_infos_async method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__fetches_all_content(
        self,
        mock_get_paginated_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_content_infos_async fetches all content across pages.
        Why this matters: Ensures all content is retrieved even when paginated.
        Setup summary: Mock paginated responses, call method, verify all content returned.
        """
        # Arrange
        import time

        content_info1 = ContentInfo(
            id="cont_test1",
            object="content",
            key="file1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        content_info2 = ContentInfo(
            id="cont_test2",
            object="content",
            key="file2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        # First call (take=1) returns total_count
        # Second call returns all content (since 2 < step_size of 100)
        mock_get_paginated_async.side_effect = [
            PaginatedContentInfos(object="list", content_infos=[], total_count=2),
            PaginatedContentInfos(
                object="list",
                content_infos=[content_info1, content_info2],
                total_count=2,
            ),
        ]

        # Act
        start_time = time.perf_counter()
        result = await base_kb_service.get_content_infos_async()
        duration = time.perf_counter() - start_time

        # Assert
        assert len(result) == 2
        assert content_info1 in result
        assert content_info2 in result
        # Log duration for performance tracking
        print(f"   ⏱️  get_content_infos_async duration: {duration:.3f}s")

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__handles_empty_content(
        self,
        mock_get_paginated_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_content_infos_async handles empty knowledge base.
        Why this matters: Edge case when no content exists.
        Setup summary: Mock empty response, verify empty list returned.
        """
        # Arrange
        mock_get_paginated_async.return_value = PaginatedContentInfos(
            object="list", content_infos=[], total_count=0
        )

        # Act
        result = await base_kb_service.get_content_infos_async()

        # Assert
        assert result == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__passes_metadata_filter(
        self,
        mock_get_paginated_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_content_infos_async passes metadata_filter to paginated calls.
        Why this matters: Allows filtering content by metadata.
        Setup summary: Call with metadata_filter, verify it's passed correctly.
        """
        # Arrange
        mock_get_paginated_async.return_value = PaginatedContentInfos(
            object="list", content_infos=[], total_count=0
        )
        metadata_filter = {"category": "reports"}

        # Act
        await base_kb_service.get_content_infos_async(metadata_filter=metadata_filter)

        # Assert
        mock_get_paginated_async.assert_called_with(
            metadata_filter=metadata_filter, take=1
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__handles_exceptions_gracefully(
        self,
        mock_get_paginated_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify get_content_infos_async handles exceptions from paginated calls.
        Why this matters: Ensures partial failures don't break entire operation.
        Setup summary: Mock some calls to raise exceptions, verify other results returned.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="file.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        # First call returns total_count, subsequent calls mix success and failure
        mock_get_paginated_async.side_effect = [
            PaginatedContentInfos(object="list", content_infos=[], total_count=200),
            PaginatedContentInfos(
                object="list", content_infos=[content_info], total_count=200
            ),
            Exception("API Error"),  # This should be caught
        ]

        # Act
        result = await base_kb_service.get_content_infos_async()

        # Assert - should return partial results, not raise exception
        assert len(result) == 1


class TestResolveVisibleFolderTreeAsync:
    """Test cases for resolve_visible_folder_tree_async method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_tree_async__returns_hierarchical_structure(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_folder_tree_async returns hierarchical folder structure.
        Why this matters: Enables displaying folder tree with files to users.
        Setup summary: Mock content infos and translation, call method, verify structure.
        """
        # Arrange
        import time

        content_info1 = ContentInfo(
            id="cont_1",
            object="content",
            key="report.pdf",
            byte_size=100,
            mime_type="application/pdf",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1/scope2"},
        )
        content_info2 = ContentInfo(
            id="cont_2",
            object="content",
            key="notes.txt",
            byte_size=50,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1"},
        )

        mock_get_content_async.return_value = [content_info1, content_info2]
        mock_translate_async.return_value = {"scope1": "Documents", "scope2": "Reports"}

        # Act
        start_time = time.perf_counter()
        result = await base_kb_service.resolve_visible_folder_tree_async()
        duration = time.perf_counter() - start_time

        # Assert
        assert isinstance(result, dict)
        assert "folders" in result
        assert "files" in result
        assert "Documents" in result["folders"]
        assert "notes.txt" in result["folders"]["Documents"]["files"]
        assert "Reports" in result["folders"]["Documents"]["folders"]
        assert (
            "report.pdf"
            in result["folders"]["Documents"]["folders"]["Reports"]["files"]
        )
        print(f"   ⏱️  resolve_visible_folder_tree_async duration: {duration:.3f}s")

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_tree_async__handles_full_path_metadata(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_folder_tree_async handles {FullPath} metadata.
        Why this matters: Some content uses {FullPath} instead of folderIdPath.
        Setup summary: Create content info with {FullPath}, verify correct tree structure.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="data.xlsx",
            byte_size=200,
            mime_type="application/vnd.ms-excel",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={r"{FullPath}": "Shared/Finance"},
        )

        mock_get_content_async.return_value = [content_info]
        mock_translate_async.return_value = {}

        # Act
        result = await base_kb_service.resolve_visible_folder_tree_async()

        # Assert
        assert "Shared" in result["folders"]
        assert "Finance" in result["folders"]["Shared"]["folders"]
        assert "data.xlsx" in result["folders"]["Shared"]["folders"]["Finance"]["files"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_tree_async__handles_empty_content(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_folder_tree_async handles empty knowledge base.
        Why this matters: Edge case when no content exists.
        Setup summary: Mock empty content, verify empty tree returned.
        """
        # Arrange
        mock_get_content_async.return_value = []
        mock_translate_async.return_value = {}

        # Act
        result = await base_kb_service.resolve_visible_folder_tree_async()

        # Assert
        assert result == {"files": [], "folders": {}}

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_tree_async__passes_metadata_filter(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify metadata_filter is passed through to content fetching.
        Why this matters: Allows filtering visible folder tree by metadata.
        Setup summary: Call with metadata_filter, verify it's passed to get_content_infos_async.
        """
        # Arrange
        mock_get_content_async.return_value = []
        mock_translate_async.return_value = {}
        metadata_filter = {"category": "reports"}

        # Act
        await base_kb_service.resolve_visible_folder_tree_async(
            metadata_filter=metadata_filter
        )

        # Assert
        mock_get_content_async.assert_called_once_with(metadata_filter=metadata_filter)


class TestResolveVisibleFilesAsync:
    """Test cases for resolve_visible_files async method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_files__returns_list_of_keys(
        self,
        mock_get_content_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_files returns list of file names (keys).
        Why this matters: Provides simple flat list of all visible files.
        Setup summary: Mock content infos, call method, verify keys returned.
        """
        # Arrange
        import time

        content_info1 = ContentInfo(
            id="cont_test1",
            object="content",
            key="documents/report.pdf",
            byte_size=100,
            mime_type="application/pdf",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        content_info2 = ContentInfo(
            id="cont_test2",
            object="content",
            key="images/photo.jpg",
            byte_size=200,
            mime_type="image/jpeg",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        mock_get_content_async.return_value = [content_info1, content_info2]

        # Act
        start_time = time.perf_counter()
        result = await base_kb_service.resolve_visible_files()
        duration = time.perf_counter() - start_time

        # Assert
        assert result == ["documents/report.pdf", "images/photo.jpg"]
        mock_get_content_async.assert_called_once_with(metadata_filter=None)
        print(f"   ⏱️  resolve_visible_files duration: {duration:.3f}s")

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_files__passes_metadata_filter(
        self,
        mock_get_content_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify metadata_filter is passed through to get_content_infos_async.
        Why this matters: Allows filtering visible files by metadata.
        Setup summary: Call with metadata_filter, verify it's passed correctly.
        """
        # Arrange
        mock_get_content_async.return_value = []
        metadata_filter = {"category": "reports"}

        # Act
        await base_kb_service.resolve_visible_files(metadata_filter=metadata_filter)

        # Assert
        mock_get_content_async.assert_called_once_with(metadata_filter=metadata_filter)

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_files__handles_empty_content(
        self,
        mock_get_content_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_files handles empty knowledge base.
        Why this matters: Edge case when no content exists.
        Setup summary: Mock empty response, verify empty list returned.
        """
        # Arrange
        mock_get_content_async.return_value = []

        # Act
        result = await base_kb_service.resolve_visible_files()

        # Assert
        assert result == []


class TestResolveVisibleFolderPathsAsync:
    """Test cases for resolve_visible_folder_paths_async method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_paths_async__returns_folder_paths(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_folder_paths_async returns list of folder paths.
        Why this matters: Provides folder structure without files.
        Setup summary: Mock content infos and translation, call method, verify paths.
        """
        # Arrange
        import time

        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="report.pdf",
            byte_size=100,
            mime_type="application/pdf",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1/scope2"},
        )

        mock_get_content_async.return_value = [content_info]
        mock_translate_async.return_value = {"scope1": "Documents", "scope2": "Reports"}

        # Act
        start_time = time.perf_counter()
        result = await base_kb_service.resolve_visible_folder_paths_async()
        duration = time.perf_counter() - start_time

        # Assert
        assert len(result) == 1
        assert result[0] == "/Documents/Reports"
        print(f"   ⏱️  resolve_visible_folder_paths_async duration: {duration:.3f}s")

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_paths_async__handles_full_path_metadata(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_folder_paths_async handles {FullPath} metadata.
        Why this matters: Content with {FullPath} already has resolved paths.
        Setup summary: Create content with {FullPath}, verify path included in results.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="data.xlsx",
            byte_size=200,
            mime_type="application/vnd.ms-excel",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={r"{FullPath}": "/Shared/Finance"},
        )

        mock_get_content_async.return_value = [content_info]
        mock_translate_async.return_value = {}

        # Act
        result = await base_kb_service.resolve_visible_folder_paths_async()

        # Assert
        assert "/Shared/Finance" in result

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_paths_async__combines_both_path_types(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_folder_paths_async combines folderIdPath and {FullPath} results.
        Why this matters: Both metadata formats should be supported simultaneously.
        Setup summary: Create content with both metadata types, verify both paths included.
        """
        # Arrange
        content_with_folder_id = ContentInfo(
            id="cont_1",
            object="content",
            key="file1.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1"},
        )
        content_with_full_path = ContentInfo(
            id="cont_2",
            object="content",
            key="file2.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={r"{FullPath}": "/External/Data"},
        )

        mock_get_content_async.return_value = [
            content_with_folder_id,
            content_with_full_path,
        ]
        mock_translate_async.return_value = {"scope1": "Documents"}

        # Act
        result = await base_kb_service.resolve_visible_folder_paths_async()

        # Assert
        assert len(result) == 2
        assert "/Documents" in result
        assert "/External/Data" in result

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_paths_async__handles_empty_content(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify resolve_visible_folder_paths_async handles empty knowledge base.
        Why this matters: Edge case when no content exists.
        Setup summary: Mock empty content, verify empty list returned.
        """
        # Arrange
        mock_get_content_async.return_value = []
        mock_translate_async.return_value = {}

        # Act
        result = await base_kb_service.resolve_visible_folder_paths_async()

        # Assert
        assert result == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_paths_async__passes_metadata_filter(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify metadata_filter is passed through to content fetching.
        Why this matters: Allows filtering visible folder paths by metadata.
        Setup summary: Call with metadata_filter, verify it's passed to get_content_infos_async.
        """
        # Arrange
        mock_get_content_async.return_value = []
        mock_translate_async.return_value = {}
        metadata_filter = {"category": "reports"}

        # Act
        await base_kb_service.resolve_visible_folder_paths_async(
            metadata_filter=metadata_filter
        )

        # Assert
        mock_get_content_async.assert_called_once_with(metadata_filter=metadata_filter)

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_to_folder_name_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_folder_paths_async__ensures_paths_start_with_slash(
        self,
        mock_get_content_async: AsyncMock,
        mock_translate_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify all returned paths start with /.
        Why this matters: Consistent path format for downstream processing.
        Setup summary: Create content with paths, verify all results start with /.
        """
        # Arrange
        content_info = ContentInfo(
            id="cont_test",
            object="content",
            key="file.txt",
            byte_size=100,
            mime_type="text/plain",
            owner_id="test_user",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
            metadata={"folderIdPath": "uniquepathid://scope1/scope2"},
        )

        mock_get_content_async.return_value = [content_info]
        mock_translate_async.return_value = {"scope1": "Root", "scope2": "SubFolder"}

        # Act
        result = await base_kb_service.resolve_visible_folder_paths_async()

        # Assert
        for path in result:
            assert path.startswith("/"), f"Path {path} should start with /"
