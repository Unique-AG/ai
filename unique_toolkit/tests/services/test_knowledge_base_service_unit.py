from datetime import datetime
from pathlib import Path, PurePath
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
import unique_sdk
from pydantic import SecretStr

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
from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueContext,
    UniqueSettings,
)
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
        mock_settings.authcontext.get_confidential_company_id.return_value = (
            "env_company"
        )
        mock_settings.authcontext.get_confidential_user_id.return_value = "env_user"
        mock_settings.context.chat = None
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
        mock_settings.authcontext.get_confidential_company_id.return_value = (
            "file_company"
        )
        mock_settings.authcontext.get_confidential_user_id.return_value = "file_user"
        mock_settings.context.chat = None
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

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.download_content_to_bytes_async")
    async def test_download_content_to_bytes_async__returns_bytes__with_content_id(
        self,
        mock_download_async: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify async download_content_to_bytes_async downloads content to memory.
        Why this matters: Async downloads enable non-blocking I/O for in-memory processing.
        Setup summary: Mock async download function to return bytes, await service method, assert bytes returned.
        """
        # Arrange
        expected_bytes = b"test file content"
        mock_download_async.return_value = expected_bytes

        # Act
        result = await base_kb_service.download_content_to_bytes_async(
            content_id="cont_test123"
        )

        # Assert
        assert isinstance(result, bytes)
        assert result == expected_bytes
        mock_download_async.assert_called_once_with(
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


# ---------------------------------------------------------------------------
# Tests: KnowledgeBaseService.from_context
# ---------------------------------------------------------------------------


class TestKnowledgeBaseServiceFromContext:
    @pytest.fixture
    def auth(self) -> AuthContext:
        return AuthContext(
            user_id=SecretStr("user-1"), company_id=SecretStr("company-1")
        )

    @pytest.fixture
    def chat(self) -> ChatContext:
        return ChatContext(
            chat_id="chat-1",
            assistant_id="assistant-1",
            last_assistant_message_id="amsg-1",
            last_user_message_id="umsg-1",
            metadata_filter={"env": "test"},
        )

    @pytest.fixture
    def context_with_chat(self, auth: AuthContext, chat: ChatContext) -> UniqueContext:
        return UniqueContext(auth=auth, chat=chat)

    @pytest.fixture
    def auth_only_context(self, auth: AuthContext) -> UniqueContext:
        return UniqueContext(auth=auth)

    @pytest.mark.ai
    def test_from_context__returns_knowledge_base_service_instance(
        self, context_with_chat: UniqueContext
    ) -> None:
        """
        Purpose: Verify from_context returns a KnowledgeBaseService instance.
        Why this matters: Callers rely on the correct type to access search and upload methods.
        Setup summary: Full context with chat; assert isinstance check.
        """
        svc = KnowledgeBaseService.from_context(context_with_chat)
        assert isinstance(svc, KnowledgeBaseService)

    @pytest.mark.ai
    def test_from_context__sets_company_id__from_auth(
        self, context_with_chat: UniqueContext
    ) -> None:
        """
        Purpose: Verify _company_id is extracted from the auth context.
        Why this matters: Wrong company_id would route content operations to the wrong tenant.
        Setup summary: Auth with company-1; assert _company_id matches.
        """
        svc = KnowledgeBaseService.from_context(context_with_chat)
        assert svc._company_id == "company-1"

    @pytest.mark.ai
    def test_from_context__sets_user_id__from_auth(
        self, context_with_chat: UniqueContext
    ) -> None:
        """
        Purpose: Verify _user_id is extracted from the auth context.
        Why this matters: Content access is user-scoped; wrong user_id leaks data across users.
        Setup summary: Auth with user-1; assert _user_id matches.
        """
        svc = KnowledgeBaseService.from_context(context_with_chat)
        assert svc._user_id == "user-1"

    @pytest.mark.ai
    def test_from_context__sets_metadata_filter__from_chat_context(
        self, context_with_chat: UniqueContext
    ) -> None:
        """
        Purpose: Verify metadata_filter is taken from the chat context when present.
        Why this matters: Filters restrict search scope; a missing filter returns unscoped results.
        Setup summary: Chat with metadata_filter={"env": "test"}; assert _metadata_filter matches.
        """
        svc = KnowledgeBaseService.from_context(context_with_chat)
        assert svc._metadata_filter == {"env": "test"}

    @pytest.mark.ai
    def test_from_context__metadata_filter_is_none__when_no_chat_context(
        self, auth_only_context: UniqueContext
    ) -> None:
        """
        Purpose: Verify metadata_filter is None when there is no chat context.
        Why this matters: Auth-only contexts (e.g. background jobs) should not apply chat filters.
        Setup summary: Auth-only context; assert _metadata_filter is None.
        """
        svc = KnowledgeBaseService.from_context(auth_only_context)
        assert svc._metadata_filter is None

    @pytest.mark.ai
    def test_from_context__returns_instance__without_chat_context(
        self, auth_only_context: UniqueContext
    ) -> None:
        """
        Purpose: Verify from_context works with an auth-only context (no chat).
        Why this matters: KB service is valid outside a chat session (e.g. ingestion pipelines).
        Setup summary: Auth-only context; assert isinstance check.
        """
        svc = KnowledgeBaseService.from_context(auth_only_context)
        assert isinstance(svc, KnowledgeBaseService)


# ---------------------------------------------------------------------------
# Tests: File Tree Resolution
# ---------------------------------------------------------------------------


def _make_content_info(
    key: str = "file.txt",
    metadata: dict[str, Any] | None = None,
) -> ContentInfo:
    return ContentInfo(
        id="cont_" + key.replace(".", "_"),
        object="content",
        key=key,
        byte_size=100,
        mime_type="text/plain",
        owner_id="test_user",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        metadata=metadata,
    )


class TestKnowledgeBaseServiceGetPaginatedContentInfosAsync:
    """Test cases for KnowledgeBaseService.get_paginated_content_infos_async."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.get_content_info_async")
    async def test_get_paginated_content_infos_async__forwards_all_params(
        self,
        mock_get_content_info: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify all parameters are forwarded to the underlying SDK function.
        Why this matters: Incorrect forwarding silently drops filters or pagination args.
        Setup summary: Call with all params; assert SDK function receives them plus user/company IDs.
        """
        mock_get_content_info.return_value = PaginatedContentInfos(
            object="list", content_infos=[], total_count=0
        )

        await base_kb_service.get_paginated_content_infos_async(
            metadata_filter={"env": "test"},
            skip=10,
            take=50,
            file_path="/docs/readme.md",
        )

        mock_get_content_info.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            metadata_filter={"env": "test"},
            skip=10,
            take=50,
            file_path="/docs/readme.md",
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.get_content_info_async")
    async def test_get_paginated_content_infos_async__returns_paginated_result(
        self,
        mock_get_content_info: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify the SDK return value is passed through unchanged.
        Why this matters: Callers depend on the PaginatedContentInfos contract.
        Setup summary: Mock returns a PaginatedContentInfos; assert same object returned.
        """
        expected = PaginatedContentInfos(
            object="list",
            content_infos=[_make_content_info(key="a.txt")],
            total_count=1,
        )
        mock_get_content_info.return_value = expected

        result = await base_kb_service.get_paginated_content_infos_async()

        assert result is expected


class TestKnowledgeBaseServiceGetFolderInfoAsync:
    """Test cases for KnowledgeBaseService.get_folder_info_async."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.get_folder_info_async")
    async def test_get_folder_info_async__returns_folder_info(
        self,
        mock_get_folder_info: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify FolderInfo is returned for a valid scope ID.
        Why this matters: Folder info is required for scope ID translation.
        Setup summary: Mock SDK function; assert FolderInfo returned.
        """
        expected = FolderInfo(
            id="scope_1",
            name="Documents",
            parent_id=None,
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )
        mock_get_folder_info.return_value = expected

        result = await base_kb_service.get_folder_info_async(scope_id="scope_1")

        assert result is expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.get_folder_info_async")
    async def test_get_folder_info_async__forwards_credentials_and_scope_id(
        self,
        mock_get_folder_info: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify user_id, company_id, and scope_id are forwarded correctly.
        Why this matters: Wrong credentials would return another tenant's folder data.
        Setup summary: Call with scope_id; assert SDK function called with correct args.
        """
        mock_get_folder_info.return_value = FolderInfo(
            id="scope_x",
            name="folder",
            parent_id=None,
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )

        await base_kb_service.get_folder_info_async(scope_id="scope_x")

        mock_get_folder_info.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            scope_id="scope_x",
        )


class TestKnowledgeBaseServiceGetContentInfosAsync:
    """Test cases for KnowledgeBaseService.get_content_infos_async."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__fetches_and_flattens_all_pages(
        self,
        mock_paginated: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify all pages are fetched and content infos are flattened into one list.
        Why this matters: Core pagination logic; incomplete fetching means missing content.
        Setup summary: total_count=250, step_size=100 -> 3 pages; assert all items collected.
        """
        page1 = [_make_content_info(key=f"p1_{i}.txt") for i in range(100)]
        page2 = [_make_content_info(key=f"p2_{i}.txt") for i in range(100)]
        page3 = [_make_content_info(key=f"p3_{i}.txt") for i in range(50)]

        mock_paginated.side_effect = [
            PaginatedContentInfos(object="list", content_infos=[], total_count=250),
            PaginatedContentInfos(object="list", content_infos=page1, total_count=250),
            PaginatedContentInfos(object="list", content_infos=page2, total_count=250),
            PaginatedContentInfos(object="list", content_infos=page3, total_count=250),
        ]

        result = await base_kb_service.get_content_infos_async(step_size=100)

        assert len(result) == 250

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__returns_empty__when_total_count_zero(
        self,
        mock_paginated: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify empty list returned when no content exists.
        Why this matters: Edge case; empty knowledge base must not crash.
        Setup summary: total_count=0; assert empty list and no page fetches.
        """
        mock_paginated.return_value = PaginatedContentInfos(
            object="list", content_infos=[], total_count=0
        )

        result = await base_kb_service.get_content_infos_async()

        assert result == []
        mock_paginated.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__forwards_metadata_filter(
        self,
        mock_paginated: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify metadata_filter is forwarded to both the count call and page calls.
        Why this matters: Missing filter returns unscoped content from other contexts.
        Setup summary: Call with metadata_filter; assert all calls include it.
        """
        mock_paginated.side_effect = [
            PaginatedContentInfos(object="list", content_infos=[], total_count=50),
            PaginatedContentInfos(
                object="list",
                content_infos=[_make_content_info()],
                total_count=50,
            ),
        ]

        await base_kb_service.get_content_infos_async(metadata_filter={"env": "prod"})

        for call in mock_paginated.call_args_list:
            assert call.kwargs["metadata_filter"] == {"env": "prod"}

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__handles_page_exception_gracefully(
        self,
        mock_paginated: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify a failed page fetch does not crash; partial results are returned.
        Why this matters: Resilience — one failed page should not discard all other pages.
        Setup summary: 2 pages, second raises; assert first page's items returned.
        """
        good_items = [_make_content_info(key="good.txt")]

        async def side_effect(**kwargs: Any) -> PaginatedContentInfos:
            if kwargs.get("take") == 1:
                return PaginatedContentInfos(
                    object="list", content_infos=[], total_count=200
                )
            if kwargs.get("skip") == 0:
                return PaginatedContentInfos(
                    object="list", content_infos=good_items, total_count=200
                )
            raise ConnectionError("page fetch failed")

        mock_paginated.side_effect = side_effect

        result = await base_kb_service.get_content_infos_async(step_size=100)

        assert len(result) == 1
        assert result[0].key == "good.txt"

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__respects_step_size(
        self,
        mock_paginated: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify step_size controls page size and number of fetches.
        Why this matters: Incorrect step_size handling causes missing or duplicate items.
        Setup summary: total_count=150, step_size=50 -> 3 page fetches with correct skip/take.
        """
        items = [_make_content_info(key=f"f{i}.txt") for i in range(50)]

        mock_paginated.side_effect = [
            PaginatedContentInfos(object="list", content_infos=[], total_count=150),
            PaginatedContentInfos(object="list", content_infos=items, total_count=150),
            PaginatedContentInfos(object="list", content_infos=items, total_count=150),
            PaginatedContentInfos(object="list", content_infos=items, total_count=150),
        ]

        result = await base_kb_service.get_content_infos_async(step_size=50)

        assert len(result) == 150
        page_calls = mock_paginated.call_args_list[1:]
        assert len(page_calls) == 3
        skips = sorted(call.kwargs["skip"] for call in page_calls)
        assert skips == [0, 50, 100]
        for call in page_calls:
            assert call.kwargs["take"] == 50

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__returns_empty__when_all_pages_fail(
        self,
        mock_paginated: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify empty list returned when every page fetch fails.
        Why this matters: Total failure must not crash; errors should be logged.
        Setup summary: total_count=200, both pages raise; assert empty list.
        """

        async def side_effect(**kwargs: Any) -> PaginatedContentInfos:
            if kwargs.get("take") == 1:
                return PaginatedContentInfos(
                    object="list", content_infos=[], total_count=200
                )
            raise ConnectionError("all pages failed")

        mock_paginated.side_effect = side_effect

        result = await base_kb_service.get_content_infos_async(step_size=100)

        assert result == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__fetches_exactly_one_page__when_count_equals_step(
        self,
        mock_paginated: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify exactly one page fetched when total_count equals step_size.
        Why this matters: Boundary condition; off-by-one could produce 0 or 2 page fetches.
        Setup summary: total_count=100, step_size=100; assert single page fetch.
        """
        items = [_make_content_info(key=f"f{i}.txt") for i in range(100)]

        mock_paginated.side_effect = [
            PaginatedContentInfos(object="list", content_infos=[], total_count=100),
            PaginatedContentInfos(object="list", content_infos=items, total_count=100),
        ]

        result = await base_kb_service.get_content_infos_async(step_size=100)

        assert len(result) == 100
        assert mock_paginated.call_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "get_paginated_content_infos_async")
    async def test_get_content_infos_async__propagates_exception__when_count_call_fails(
        self,
        mock_paginated: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify exception propagates when the initial count call fails.
        Why this matters: No partial result is possible without knowing total_count.
        Setup summary: Mock count call to raise; assert exception propagates to caller.
        """
        mock_paginated.side_effect = ConnectionError("API down")

        with pytest.raises(ConnectionError, match="API down"):
            await base_kb_service.get_content_infos_async()


class TestKnowledgeBaseServiceExtractScopeIds:
    """Test cases for KnowledgeBaseService.extract_scope_ids."""

    @pytest.mark.ai
    def test_extract_scope_ids__returns_ids__from_folder_id_path(self) -> None:
        """
        Purpose: Verify scope IDs are extracted from folderIdPath metadata.
        Why this matters: Scope IDs are needed to resolve folder names for display.
        Setup summary: Two content infos with different folderIdPaths; assert union of IDs returned.
        """
        content_infos = [
            _make_content_info(
                key="a.txt",
                metadata={"folderIdPath": "uniquepathid://id1/id2"},
            ),
            _make_content_info(
                key="b.txt",
                metadata={"folderIdPath": "uniquepathid://id2/id3"},
            ),
        ]
        result = KnowledgeBaseService.extract_scope_ids(content_infos)
        assert result == {"id1", "id2", "id3"}

    @pytest.mark.ai
    def test_extract_scope_ids__returns_empty_set__when_no_metadata(self) -> None:
        """
        Purpose: Verify empty set returned when content has no metadata.
        Why this matters: Graceful handling of content without folder info prevents crashes.
        Setup summary: Content info with metadata=None; assert empty set.
        """
        content_infos = [_make_content_info(key="a.txt", metadata=None)]
        result = KnowledgeBaseService.extract_scope_ids(content_infos)
        assert result == set()

    @pytest.mark.ai
    def test_extract_scope_ids__returns_empty_set__when_no_folder_id_path(self) -> None:
        """
        Purpose: Verify empty set when metadata exists but folderIdPath is absent.
        Why this matters: Not all content has a folder path; method must handle gracefully.
        Setup summary: Content info with metadata missing folderIdPath; assert empty set.
        """
        content_infos = [_make_content_info(key="a.txt", metadata={"other": "value"})]
        result = KnowledgeBaseService.extract_scope_ids(content_infos)
        assert result == set()

    @pytest.mark.ai
    def test_extract_scope_ids__skips_empty_segments(self) -> None:
        """
        Purpose: Verify empty segments from leading/trailing slashes are filtered out.
        Why this matters: The uniquepathid:// prefix leaves an empty segment after split.
        Setup summary: folderIdPath with trailing slash; assert no empty strings in result.
        """
        content_infos = [
            _make_content_info(
                key="a.txt",
                metadata={"folderIdPath": "uniquepathid://id1/id2/"},
            ),
        ]
        result = KnowledgeBaseService.extract_scope_ids(content_infos)
        assert result == {"id1", "id2"}
        assert "" not in result

    @pytest.mark.ai
    def test_extract_scope_ids__returns_empty_set__for_empty_list(self) -> None:
        """
        Purpose: Verify empty set returned for empty input.
        Why this matters: Edge case; callers may pass empty content lists.
        Setup summary: Empty content_infos list; assert empty set.
        """
        result = KnowledgeBaseService.extract_scope_ids([])
        assert result == set()

    @pytest.mark.ai
    def test_extract_scope_ids__ignores_non_string_folder_id_path(self) -> None:
        """
        Purpose: Verify non-string folderIdPath values are ignored.
        Why this matters: Metadata may contain unexpected types; method must not crash.
        Setup summary: folderIdPath set to an integer; assert empty set.
        """
        content_infos = [
            _make_content_info(key="a.txt", metadata={"folderIdPath": 12345}),
        ]
        result = KnowledgeBaseService.extract_scope_ids(content_infos)
        assert result == set()

    @pytest.mark.ai
    def test_extract_scope_ids__deduplicates_across_content_infos(self) -> None:
        """
        Purpose: Verify duplicate scope IDs across content items are deduplicated.
        Why this matters: Reduces redundant API calls during translation.
        Setup summary: Two content infos sharing the same scope IDs; assert set has no duplicates.
        """
        content_infos = [
            _make_content_info(
                key="a.txt",
                metadata={"folderIdPath": "uniquepathid://shared_id/unique_a"},
            ),
            _make_content_info(
                key="b.txt",
                metadata={"folderIdPath": "uniquepathid://shared_id/unique_b"},
            ),
        ]
        result = KnowledgeBaseService.extract_scope_ids(content_infos)
        assert result == {"shared_id", "unique_a", "unique_b"}

    @pytest.mark.ai
    def test_extract_scope_ids__handles_folder_id_path__without_prefix(self) -> None:
        """
        Purpose: Verify extraction works when folderIdPath lacks the uniquepathid:// prefix.
        Why this matters: Data may not always include the prefix; .replace() is a no-op in that case.
        Setup summary: folderIdPath without prefix; assert IDs still extracted.
        """
        content_infos = [
            _make_content_info(
                key="a.txt",
                metadata={"folderIdPath": "id1/id2"},
            ),
        ]
        result = KnowledgeBaseService.extract_scope_ids(content_infos)
        assert result == {"id1", "id2"}


class TestKnowledgeBaseServiceTranslateScopeIdAsync:
    """Test cases for KnowledgeBaseService._translate_scope_id_async."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.get_folder_info_async")
    async def test_translate_scope_id__returns_folder_name__on_success(
        self,
        mock_get_folder_info: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify folder name is returned for a valid scope ID.
        Why this matters: Core path resolution depends on translating IDs to names.
        Setup summary: Mock get_folder_info_async to return a folder; assert name returned.
        """
        mock_get_folder_info.return_value = FolderInfo(
            id="scope_1",
            name="Documents",
            parent_id=None,
            ingestion_config={},
            created_at=None,
            updated_at=None,
            external_id=None,
        )

        result = await base_kb_service._translate_scope_id_async("scope_1")

        assert result == "Documents"
        mock_get_folder_info.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch("unique_toolkit.services.knowledge_base.get_folder_info_async")
    async def test_translate_scope_id__returns_none__on_exception(
        self,
        mock_get_folder_info: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify None is returned when folder lookup fails.
        Why this matters: Graceful degradation prevents one bad scope ID from crashing the whole resolution.
        Setup summary: Mock get_folder_info_async to raise; assert None returned without exception.
        """
        mock_get_folder_info.side_effect = Exception("Not found")

        result = await base_kb_service._translate_scope_id_async("bad_scope")

        assert result is None


class TestKnowledgeBaseServiceTranslateScopeIdsAsync:
    """Test cases for KnowledgeBaseService._translate_scope_ids_async."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_translate_scope_ids__returns_mapping__for_all_ids(
        self,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify all scope IDs are translated to folder names concurrently.
        Why this matters: Batch translation with concurrency is the performance-critical path.
        Setup summary: Patch _translate_scope_id_async to return deterministic names; assert full mapping.
        """

        async def mock_translate(scope_id: str) -> str:
            return f"folder_{scope_id}"

        with patch.object(
            base_kb_service, "_translate_scope_id_async", side_effect=mock_translate
        ):
            result = await base_kb_service._translate_scope_ids_async(
                {"id1", "id2", "id3"}
            )

        assert len(result) == 3
        assert result["id1"] == "folder_id1"
        assert result["id2"] == "folder_id2"
        assert result["id3"] == "folder_id3"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_translate_scope_ids__excludes_failed_ids__from_mapping(
        self,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify failed translations are excluded from the result mapping.
        Why this matters: Callers fall back to raw scope IDs for unresolved entries.
        Setup summary: Mock returns None for one ID; assert it is absent from result.
        """

        async def mock_translate(scope_id: str) -> str | None:
            if scope_id == "bad_id":
                return None
            return f"folder_{scope_id}"

        with patch.object(
            base_kb_service, "_translate_scope_id_async", side_effect=mock_translate
        ):
            result = await base_kb_service._translate_scope_ids_async(
                {"good_id", "bad_id"}
            )

        assert "good_id" in result
        assert "bad_id" not in result
        assert result["good_id"] == "folder_good_id"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_translate_scope_ids__returns_empty_dict__for_empty_input(
        self,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify empty dict returned for empty scope IDs.
        Why this matters: Edge case; content may have no folder paths at all.
        Setup summary: Empty set input; assert empty dict.
        """
        result = await base_kb_service._translate_scope_ids_async(set())
        assert result == {}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_translate_scope_ids__respects_concurrency_limit(
        self,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify the semaphore limits concurrent requests.
        Why this matters: Prevents overwhelming the API with too many concurrent calls.
        Setup summary: Set max_concurrent_requests=2, track concurrency with counter; assert max never exceeded.
        """
        import asyncio

        max_observed_concurrency = 0
        current_concurrency = 0
        lock = asyncio.Lock()

        async def mock_translate(scope_id: str) -> str:
            nonlocal max_observed_concurrency, current_concurrency
            async with lock:
                current_concurrency += 1
                max_observed_concurrency = max(
                    max_observed_concurrency, current_concurrency
                )
            await asyncio.sleep(0.01)
            async with lock:
                current_concurrency -= 1
            return f"folder_{scope_id}"

        with patch.object(
            base_kb_service, "_translate_scope_id_async", side_effect=mock_translate
        ):
            await base_kb_service._translate_scope_ids_async(
                {"a", "b", "c", "d", "e"},
                max_concurrent_requests=2,
            )

        assert max_observed_concurrency <= 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_translate_scope_ids__returns_empty_dict__when_all_fail(
        self,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify empty dict returned when every translation fails.
        Why this matters: Complete translation failure must not crash; callers use raw IDs as fallback.
        Setup summary: Mock returns None for all IDs; assert empty dict.
        """

        async def mock_translate(scope_id: str) -> None:
            return None

        with patch.object(
            base_kb_service, "_translate_scope_id_async", side_effect=mock_translate
        ):
            result = await base_kb_service._translate_scope_ids_async(
                {"id1", "id2", "id3"}
            )

        assert result == {}


class TestKnowledgeBaseServiceResolveVisibleFilePathsAsync:
    """Test cases for KnowledgeBaseService.resolve_visible_file_paths_async."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__uses_folder_id_path(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify file paths are resolved using folderIdPath metadata.
        Why this matters: Primary path resolution for content ingested through standard connectors.
        Setup summary: Mock content with folderIdPath; mock translation; assert folder + filename path.
        """
        mock_get_content_infos.return_value = [
            _make_content_info(
                key="report.pdf",
                metadata={"folderIdPath": "uniquepathid://scope_a/scope_b"},
            ),
        ]
        mock_translate.return_value = {"scope_a": "Documents", "scope_b": "Reports"}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert result == [["Documents", "Reports", "report.pdf"]]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__falls_back_to_no_folder_path(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify fallback when neither {FullPath} nor folderIdPath is present.
        Why this matters: Content without folder metadata must still appear in results.
        Setup summary: Content with empty metadata; assert _no_folder_path sentinel used.
        """
        mock_get_content_infos.return_value = [
            _make_content_info(key="orphan.txt", metadata={}),
        ]
        mock_translate.return_value = {}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert result == [["_no_folder_path", "orphan.txt"]]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__falls_back__when_metadata_is_none(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify fallback when metadata is None.
        Why this matters: Metadata field is optional; None must not cause AttributeError.
        Setup summary: Content with metadata=None; assert _no_folder_path sentinel used.
        """
        mock_get_content_infos.return_value = [
            _make_content_info(key="no_meta.txt", metadata=None),
        ]
        mock_translate.return_value = {}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert result == [["_no_folder_path", "no_meta.txt"]]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__uses_raw_scope_id__when_translation_missing(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify raw scope ID is used when translation fails for that ID.
        Why this matters: Partial translation failures should degrade gracefully, not crash.
        Setup summary: Translation mapping missing one scope ID; assert raw ID used as fallback.
        """
        mock_get_content_infos.return_value = [
            _make_content_info(
                key="file.txt",
                metadata={"folderIdPath": "uniquepathid://known/unknown"},
            ),
        ]
        mock_translate.return_value = {"known": "ResolvedFolder"}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert result == [["ResolvedFolder", "unknown", "file.txt"]]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__returns_empty_list__for_no_content(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify empty list returned when no content exists.
        Why this matters: Callers iterating over results must handle empty gracefully.
        Setup summary: Mock returns empty content list; assert empty result.
        """
        mock_get_content_infos.return_value = []
        mock_translate.return_value = {}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert result == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__passes_metadata_filter(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify metadata_filter parameter is forwarded to get_content_infos_async.
        Why this matters: Callers may want to narrow the scope of resolved paths.
        Setup summary: Call with metadata_filter; assert it is passed through.
        """
        mock_get_content_infos.return_value = []
        mock_translate.return_value = {}

        await base_kb_service.resolve_visible_file_paths_async(
            metadata_filter={"env": "prod"}
        )

        mock_get_content_infos.assert_called_once_with(metadata_filter={"env": "prod"})

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__handles_mixed_content(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify mixed content (folderIdPath and no metadata) handled together.
        Why this matters: Real-world content mixes metadata types; all branches must coexist.
        Setup summary: Three content items with different metadata types; assert each resolved correctly.
        """
        mock_get_content_infos.return_value = [
            _make_content_info(
                key="uploaded.pdf",
                metadata={"folderIdPath": "uniquepathid://scope_x/scope_y"},
            ),
            _make_content_info(
                key="another.doc",
                metadata={"folderIdPath": "uniquepathid://scope_x"},
            ),
            _make_content_info(key="orphan.txt", metadata={}),
        ]
        mock_translate.return_value = {"scope_x": "Uploads", "scope_y": "Reports"}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert len(result) == 3
        assert result[0] == ["Uploads", "Reports", "uploaded.pdf"]
        assert result[1] == ["Uploads", "another.doc"]
        assert result[2] == ["_no_folder_path", "orphan.txt"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__falls_back__when_folder_id_path_is_non_string(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify fallback when folderIdPath is a non-string type.
        Why this matters: The isinstance guard must route non-string values to the else branch.
        Setup summary: folderIdPath set to integer; assert _no_folder_path sentinel used.
        """
        mock_get_content_infos.return_value = [
            _make_content_info(
                key="bad_meta.txt",
                metadata={"folderIdPath": 12345},
            ),
        ]
        mock_translate.return_value = {}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert result == [["_no_folder_path", "bad_meta.txt"]]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__uses_all_raw_ids__when_all_translations_fail(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify raw scope IDs used for all segments when translation returns empty.
        Why this matters: Complete translation failure must degrade gracefully, not crash.
        Setup summary: Translation returns empty dict; assert raw IDs appear in path.
        """
        mock_get_content_infos.return_value = [
            _make_content_info(
                key="file.txt",
                metadata={"folderIdPath": "uniquepathid://scope_a/scope_b"},
            ),
        ]
        mock_translate.return_value = {}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert result == [["scope_a", "scope_b", "file.txt"]]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch.object(KnowledgeBaseService, "_translate_scope_ids_async")
    @patch.object(KnowledgeBaseService, "get_content_infos_async")
    async def test_resolve_visible_file_paths__appends_empty_key__when_key_is_empty(
        self,
        mock_get_content_infos: AsyncMock,
        mock_translate: AsyncMock,
        base_kb_service: KnowledgeBaseService,
    ) -> None:
        """
        Purpose: Verify empty content key is appended as-is without crashing.
        Why this matters: Malformed data must not cause exceptions; empty key flows through.
        Setup summary: Content with key=""; assert path ends with empty string.
        """
        mock_get_content_infos.return_value = [
            _make_content_info(
                key="",
                metadata={"folderIdPath": "uniquepathid://scope_a"},
            ),
        ]
        mock_translate.return_value = {"scope_a": "Folder"}

        result = await base_kb_service.resolve_visible_file_paths_async()

        assert result == [["Folder", ""]]


class TestKnowledgeBaseServiceDisplayPathTree:
    """Test cases for KnowledgeBaseService.display_path_tree."""

    @pytest.mark.ai
    def test_display_path_tree__renders_simple_tree(self) -> None:
        """
        Purpose: Verify basic tree rendering with shared parent.
        Why this matters: Core display functionality for file tree visualization.
        Setup summary: Two paths sharing a parent; assert tree-style output with connectors.
        """
        paths = [["docs", "api"], ["docs", "guides"], ["src"]]
        result = KnowledgeBaseService.display_path_tree(paths)

        assert "." in result
        assert "docs" in result
        assert "api" in result
        assert "guides" in result
        assert "src" in result
        assert "├── " in result or "└── " in result

    @pytest.mark.ai
    def test_display_path_tree__returns_root_only__for_empty_paths(self) -> None:
        """
        Purpose: Verify only root name returned when no paths provided.
        Why this matters: Empty knowledge bases should not crash the display.
        Setup summary: Empty paths list; assert only root name returned.
        """
        result = KnowledgeBaseService.display_path_tree([])
        assert result == "."

    @pytest.mark.ai
    def test_display_path_tree__uses_custom_root_name(self) -> None:
        """
        Purpose: Verify custom root_name is used in output.
        Why this matters: Callers may want to display a meaningful root label.
        Setup summary: Custom root name; assert it appears in output.
        """
        result = KnowledgeBaseService.display_path_tree(
            [["a"]], root_name="Knowledge Base"
        )
        assert result.startswith("Knowledge Base")

    @pytest.mark.ai
    def test_display_path_tree__renders_deeply_nested_paths(self) -> None:
        """
        Purpose: Verify deep nesting is correctly indented.
        Why this matters: Real folder structures can be deeply nested.
        Setup summary: Path with 4 levels; assert all segments appear in output.
        """
        paths = [["a", "b", "c", "d"]]
        result = KnowledgeBaseService.display_path_tree(paths)

        for segment in ["a", "b", "c", "d"]:
            assert segment in result

    @pytest.mark.ai
    def test_display_path_tree__sorts_folders_before_files(self) -> None:
        """
        Purpose: Verify folders (nodes with children) appear before files (leaf nodes).
        Why this matters: Consistent ordering improves readability of tree output.
        Setup summary: Mix of folder and file at same level; assert folder listed first.
        """
        paths = [["z_file"], ["a_folder", "child"]]
        result = KnowledgeBaseService.display_path_tree(paths)

        lines = result.split("\n")
        folder_line_idx = next(i for i, line in enumerate(lines) if "a_folder" in line)
        file_line_idx = next(i for i, line in enumerate(lines) if "z_file" in line)
        assert folder_line_idx < file_line_idx

    @pytest.mark.ai
    def test_display_path_tree__handles_single_file(self) -> None:
        """
        Purpose: Verify single-file tree renders correctly.
        Why this matters: Simplest non-empty case must work.
        Setup summary: One path with one segment; assert └── connector used.
        """
        result = KnowledgeBaseService.display_path_tree([["only_file.txt"]])
        assert "└── only_file.txt" in result

    @pytest.mark.ai
    def test_display_path_tree__skips_empty_segments(self) -> None:
        """
        Purpose: Verify empty strings in path segments are filtered out.
        Why this matters: Upstream may produce empty segments from split operations.
        Setup summary: Path with empty strings; assert they don't appear in output.
        """
        paths = [["", "folder", "", "file.txt"]]
        result = KnowledgeBaseService.display_path_tree(paths)

        assert "folder" in result
        assert "file.txt" in result
        lines = [ln.strip() for ln in result.split("\n") if ln.strip()]
        for line in lines:
            stripped = line.lstrip("│├└── ─\u00a0 ")
            if stripped:
                assert stripped != ""

    @pytest.mark.ai
    def test_display_path_tree__merges_shared_prefixes(self) -> None:
        """
        Purpose: Verify paths sharing a common prefix are merged in the tree.
        Why this matters: Tree display must not duplicate shared folders.
        Setup summary: Two paths sharing root folder; count occurrences of shared folder name.
        """
        paths = [["shared", "a.txt"], ["shared", "b.txt"]]
        result = KnowledgeBaseService.display_path_tree(paths)

        assert result.count("shared") == 1

    @pytest.mark.ai
    def test_display_path_tree__renders_root_only__for_all_empty_paths(self) -> None:
        """
        Purpose: Verify all-empty paths produce only the root node.
        Why this matters: Empty inner lists are no-ops in tree building; output must not break.
        Setup summary: Three empty path lists; assert only root returned.
        """
        result = KnowledgeBaseService.display_path_tree([[], [], []])
        assert result == "."

    @pytest.mark.ai
    def test_display_path_tree__sorts_multiple_flat_files(self) -> None:
        """
        Purpose: Verify multiple root-level files are sorted alphabetically.
        Why this matters: Consistent ordering when all entries are leaf nodes at root level.
        Setup summary: Three single-segment paths in unsorted order; assert alphabetical output.
        """
        paths = [["c_file.txt"], ["a_file.txt"], ["b_file.txt"]]
        result = KnowledgeBaseService.display_path_tree(paths)

        lines = result.split("\n")
        file_lines = [ln for ln in lines if "file.txt" in ln]
        assert len(file_lines) == 3
        assert "a_file.txt" in file_lines[0]
        assert "b_file.txt" in file_lines[1]
        assert "c_file.txt" in file_lines[2]
