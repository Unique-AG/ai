"""
Tests for content schemas to ensure 100% coverage.
These tests focus on schema validation, serialization, and edge cases.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentMetadata,
    ContentReference,
    ContentRerankerConfig,
    ContentSearchResult,
    ContentSearchType,
    ContentUploadInput,
)


@pytest.mark.ai
class TestContentSchemas:
    """Tests for content schemas to ensure 100% coverage."""

    def test_content_metadata__basic_creation_AI(self):
        """
        Purpose: Verify ContentMetadata can be created with required fields.
        Why this matters: Tests basic schema validation for metadata.
        Setup summary: Create ContentMetadata with required fields.
        """
        # Arrange & Act
        metadata = ContentMetadata(key="test_key", mime_type="application/pdf")

        # Assert
        assert metadata.key == "test_key"
        assert metadata.mime_type == "application/pdf"

    def test_content_metadata__with_extra_fields_AI(self):
        """
        Purpose: Verify ContentMetadata accepts extra fields due to extra="allow".
        Why this matters: Tests schema flexibility for additional metadata.
        Setup summary: Create ContentMetadata with extra fields.
        """
        # Arrange & Act
        metadata = ContentMetadata(
            key="test_key",
            mime_type="application/pdf",
            extra_field="extra_value",
            another_field=123,
        )

        # Assert
        assert metadata.key == "test_key"
        assert metadata.mime_type == "application/pdf"
        assert metadata.extra_field == "extra_value"
        assert metadata.another_field == 123

    def test_content_chunk__with_all_fields_AI(self, base_content_chunk):
        """
        Purpose: Verify ContentChunk can be created with all fields.
        Why this matters: Tests complete schema validation for content chunks.
        Setup summary: Use base_content_chunk fixture and add additional fields.
        """
        # Arrange
        now = datetime.now()
        metadata = ContentMetadata(key="chunk_key", mime_type="text/plain")
        chunk = base_content_chunk
        chunk.id = "cont_123456789012345678901234"
        chunk.text = "Sample chunk text"
        chunk.order = 1
        chunk.key = "chunk_key"
        chunk.chunk_id = "chunk_12345678901234567890123"
        chunk.url = "https://example.com/chunk"
        chunk.title = "Chunk Title"
        chunk.start_page = 1
        chunk.end_page = 2
        chunk.object = "chunk"
        chunk.metadata = metadata
        chunk.internally_stored_at = now
        chunk.created_at = now
        chunk.updated_at = now

        # Act & Assert
        assert chunk.id == "cont_123456789012345678901234"
        assert chunk.text == "Sample chunk text"
        assert chunk.order == 1
        assert chunk.key == "chunk_key"
        assert chunk.chunk_id == "chunk_12345678901234567890123"
        assert chunk.url == "https://example.com/chunk"
        assert chunk.title == "Chunk Title"
        assert chunk.start_page == 1
        assert chunk.end_page == 2
        assert chunk.object == "chunk"
        assert chunk.metadata == metadata
        assert chunk.internally_stored_at == now
        assert chunk.created_at == now
        assert chunk.updated_at == now

    def test_content_chunk__with_defaults_AI(self):
        """
        Purpose: Verify ContentChunk uses default values correctly.
        Why this matters: Tests default value handling in schema.
        Setup summary: Create ContentChunk with minimal fields.
        """
        # Act
        chunk = ContentChunk()

        # Assert
        assert chunk.id == ""
        assert chunk.text == ""
        assert chunk.order == 0
        assert chunk.key is None
        assert chunk.chunk_id is None
        assert chunk.url is None
        assert chunk.title is None
        assert chunk.start_page is None
        assert chunk.end_page is None
        assert chunk.object is None
        assert chunk.metadata is None
        assert chunk.internally_stored_at is None
        assert chunk.created_at is None
        assert chunk.updated_at is None

    def test_content__with_all_fields_AI(self):
        """
        Purpose: Verify Content can be created with all fields.
        Why this matters: Tests complete schema validation for content.
        Setup summary: Create Content with all possible fields.
        """
        # Arrange
        now = datetime.now()
        chunks = [
            ContentChunk(id="cont_1", text="Chunk 1", order=1),
            ContentChunk(id="cont_1", text="Chunk 2", order=2),
        ]

        # Act
        content = Content(
            id="cont_123456789012345678901234",
            key="content_key",
            title="Content Title",
            url="https://example.com/content",
            chunks=chunks,
            write_url="https://example.com/write",
            read_url="https://example.com/read",
            created_at=now,
            updated_at=now,
            metadata={"key": "value"},
            ingestion_config={"chunk_size": 1000},
        )

        # Assert
        assert content.id == "cont_123456789012345678901234"
        assert content.key == "content_key"
        assert content.title == "Content Title"
        assert content.url == "https://example.com/content"
        assert content.chunks == chunks
        assert content.write_url == "https://example.com/write"
        assert content.read_url == "https://example.com/read"
        assert content.created_at == now
        assert content.updated_at == now
        assert content.metadata == {"key": "value"}
        assert content.ingestion_config == {"chunk_size": 1000}

    def test_content__with_defaults_AI(self):
        """
        Purpose: Verify Content uses default values correctly.
        Why this matters: Tests default value handling in schema.
        Setup summary: Create Content with minimal fields.
        """
        # Act
        content = Content()

        # Assert
        assert content.id == ""
        assert content.key == ""
        assert content.title is None
        assert content.url is None
        assert content.chunks == []
        assert content.write_url is None
        assert content.read_url is None
        assert content.created_at is None
        assert content.updated_at is None
        assert content.metadata is None
        assert content.ingestion_config is None

    def test_content_reference__with_all_fields_AI(self):
        """
        Purpose: Verify ContentReference can be created with all fields.
        Why this matters: Tests complete schema validation for content references.
        Setup summary: Create ContentReference with all possible fields.
        """
        # Act
        reference = ContentReference(
            id="ref_123456789012345678901234",
            message_id="msg_123456789012345678901234",
            name="Reference Name",
            sequence_number=1,
            source="document",
            source_id="doc_123456789012345678901234",
            url="https://example.com/reference",
            original_index=[0, 1, 2],
        )

        # Assert
        assert reference.id == "ref_123456789012345678901234"
        assert reference.message_id == "msg_123456789012345678901234"
        assert reference.name == "Reference Name"
        assert reference.sequence_number == 1
        assert reference.source == "document"
        assert reference.source_id == "doc_123456789012345678901234"
        assert reference.url == "https://example.com/reference"
        assert reference.original_index == [0, 1, 2]

    def test_content_reference__with_defaults_AI(self):
        """
        Purpose: Verify ContentReference uses default values correctly.
        Why this matters: Tests default value handling in schema.
        Setup summary: Create ContentReference with minimal fields.
        """
        # Act
        reference = ContentReference(
            name="Reference Name",
            sequence_number=1,
            source="document",
            source_id="doc_123456789012345678901234",
            url="https://example.com/reference",
        )

        # Assert
        assert reference.id == ""
        assert reference.message_id == ""
        assert reference.name == "Reference Name"
        assert reference.sequence_number == 1
        assert reference.source == "document"
        assert reference.source_id == "doc_123456789012345678901234"
        assert reference.url == "https://example.com/reference"
        assert reference.original_index == []

    def test_content_search_type__enum_values_AI(self):
        """
        Purpose: Verify ContentSearchType enum has correct values.
        Why this matters: Tests enum definition for search types.
        Setup summary: Test all enum values.
        """
        # Assert
        assert ContentSearchType.COMBINED == "COMBINED"
        assert ContentSearchType.VECTOR == "VECTOR"

    def test_content_search_result__with_all_fields_AI(self):
        """
        Purpose: Verify ContentSearchResult can be created with all fields.
        Why this matters: Tests complete schema validation for search results.
        Setup summary: Create ContentSearchResult with all possible fields.
        """
        # Act
        result = ContentSearchResult(
            id="result_123456789012345678901234",
            text="Search result text",
            order=1,
            chunkId="chunk_12345678901234567890123",
            key="result_key",
            title="Result Title",
            url="https://example.com/result",
            startPage=1,
            endPage=2,
            object="search_result",
        )

        # Assert
        assert result.id == "result_123456789012345678901234"
        assert result.text == "Search result text"
        assert result.order == 1
        assert result.chunkId == "chunk_12345678901234567890123"
        assert result.key == "result_key"
        assert result.title == "Result Title"
        assert result.url == "https://example.com/result"
        assert result.startPage == 1
        assert result.endPage == 2
        assert result.object == "search_result"

    def test_content_search_result__with_defaults_AI(self):
        """
        Purpose: Verify ContentSearchResult uses default values correctly.
        Why this matters: Tests default value handling in schema.
        Setup summary: Create ContentSearchResult with minimal fields.
        """
        # Act
        result = ContentSearchResult(
            id="result_123456789012345678901234",
            text="Search result text",
            order=1,
        )

        # Assert
        assert result.id == "result_123456789012345678901234"
        assert result.text == "Search result text"
        assert result.order == 1
        assert result.chunkId is None
        assert result.key is None
        assert result.title is None
        assert result.url is None
        assert result.startPage is None
        assert result.endPage is None
        assert result.object is None

    def test_content_upload_input__with_all_fields_AI(self):
        """
        Purpose: Verify ContentUploadInput can be created with all fields.
        Why this matters: Tests complete schema validation for upload input.
        Setup summary: Create ContentUploadInput with all possible fields.
        """
        # Act
        upload_input = ContentUploadInput(
            key="upload_key",
            title="Upload Title",
            mime_type="application/pdf",
            owner_type="user",
            owner_id="user_123456789012345678901234",
            byte_size=1024,
        )

        # Assert
        assert upload_input.key == "upload_key"
        assert upload_input.title == "Upload Title"
        assert upload_input.mime_type == "application/pdf"
        assert upload_input.owner_type == "user"
        assert upload_input.owner_id == "user_123456789012345678901234"
        assert upload_input.byte_size == 1024

    def test_content_upload_input__with_required_fields_only_AI(self):
        """
        Purpose: Verify ContentUploadInput can be created with required fields only.
        Why this matters: Tests schema validation with minimal required fields.
        Setup summary: Create ContentUploadInput with only required fields.
        """
        # Act
        upload_input = ContentUploadInput(
            key="upload_key",
            title="Upload Title",
            mime_type="application/pdf",
        )

        # Assert
        assert upload_input.key == "upload_key"
        assert upload_input.title == "Upload Title"
        assert upload_input.mime_type == "application/pdf"
        assert upload_input.owner_type is None
        assert upload_input.owner_id is None
        assert upload_input.byte_size is None

    def test_content_reranker_config__with_all_fields_AI(self):
        """
        Purpose: Verify ContentRerankerConfig can be created with all fields.
        Why this matters: Tests complete schema validation for reranker config.
        Setup summary: Create ContentRerankerConfig with all possible fields.
        """
        # Act
        config = ContentRerankerConfig(
            deployment_name="test-deployment",
            options={"model": "test-model", "temperature": 0.7},
        )

        # Assert
        assert config.deployment_name == "test-deployment"
        assert config.options == {"model": "test-model", "temperature": 0.7}

    def test_content_reranker_config__with_required_fields_only_AI(self):
        """
        Purpose: Verify ContentRerankerConfig can be created with required fields only.
        Why this matters: Tests schema validation with minimal required fields.
        Setup summary: Create ContentRerankerConfig with only required fields.
        """
        # Act
        config = ContentRerankerConfig(deployment_name="test-deployment")

        # Assert
        assert config.deployment_name == "test-deployment"
        assert config.options is None

    def test_content_reranker_config__serialization_alias_AI(self):
        """
        Purpose: Verify ContentRerankerConfig uses correct serialization alias.
        Why this matters: Tests serialization alias for deploymentName field.
        Setup summary: Test model_dump with by_alias=True.
        """
        # Arrange
        config = ContentRerankerConfig(
            deployment_name="test-deployment",
            options={"model": "test-model"},
        )

        # Act
        serialized = config.model_dump(by_alias=True)

        # Assert
        assert "deploymentName" in serialized
        assert serialized["deploymentName"] == "test-deployment"
        assert "deployment_name" not in serialized

    def test_content_chunk__validation_error_AI(self):
        """
        Purpose: Verify ContentChunk raises ValidationError for invalid data.
        Why this matters: Tests schema validation error handling.
        Setup summary: Attempt to create ContentChunk with invalid data.
        """
        # Act & Assert
        with pytest.raises(ValidationError):
            ContentChunk(id="invalid_id", text=123)  # text should be string

    def test_content__validation_error_AI(self):
        """
        Purpose: Verify Content raises ValidationError for invalid data.
        Why this matters: Tests schema validation error handling.
        Setup summary: Attempt to create Content with invalid data.
        """
        # Act & Assert
        with pytest.raises(ValidationError):
            Content(id="invalid_id", key=123)  # key should be string

    def test_content_reference__validation_error_AI(self):
        """
        Purpose: Verify ContentReference raises ValidationError for invalid data.
        Why this matters: Tests schema validation error handling.
        Setup summary: Attempt to create ContentReference with invalid data.
        """
        # Act & Assert
        with pytest.raises(ValidationError):
            ContentReference(
                name="test",
                sequence_number="invalid",  # should be int
                source="test",
                source_id="test",
                url="test",
            )

    def test_content_search_result__validation_error_AI(self):
        """
        Purpose: Verify ContentSearchResult raises ValidationError for invalid data.
        Why this matters: Tests schema validation error handling.
        Setup summary: Attempt to create ContentSearchResult with invalid data.
        """
        # Act & Assert
        with pytest.raises(ValidationError):
            ContentSearchResult(
                id="test",
                text="test",
                order="invalid",  # should be int
            )

    def test_content_upload_input__validation_error_AI(self):
        """
        Purpose: Verify ContentUploadInput raises ValidationError for invalid data.
        Why this matters: Tests schema validation error handling.
        Setup summary: Attempt to create ContentUploadInput with invalid data.
        """
        # Act & Assert
        with pytest.raises(ValidationError):
            ContentUploadInput(
                key="test",
                title=123,  # should be string
                mime_type="test",
            )

    def test_content_reranker_config__validation_error_AI(self):
        """
        Purpose: Verify ContentRerankerConfig raises ValidationError for invalid data.
        Why this matters: Tests schema validation error handling.
        Setup summary: Attempt to create ContentRerankerConfig with invalid data.
        """
        # Act & Assert
        with pytest.raises(ValidationError):
            ContentRerankerConfig(
                deployment_name=123,  # should be string
            )
