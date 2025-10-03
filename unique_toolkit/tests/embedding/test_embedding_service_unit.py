from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.embedding.schemas import Embeddings
from unique_toolkit.embedding.service import EmbeddingService


@pytest.fixture
def sample_embedding_data():
    """Sample embedding data for testing."""
    return {
        "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    }


@pytest.fixture
def sample_texts():
    """Sample texts for embedding."""
    return ["Hello world", "Test embedding"]


class TestEmbeddingServiceUnit:
    @pytest.mark.ai_generated
    def test_embed_texts__returns_embeddings_object__when_successful_AI(
        self, sample_embedding_data, sample_texts
    ):
        """
        Purpose: Verify that EmbeddingService.embed_texts returns a proper Embeddings object.
        Why this matters: Core service functionality for text embedding must work correctly.
        Setup summary: Mock SDK response with sample embedding data.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")

        with patch.object(unique_sdk.Embeddings, "create") as mock_create:
            mock_create.return_value = sample_embedding_data

            # Act
            result = service.embed_texts(sample_texts)

            # Assert
            assert isinstance(result, Embeddings)
            assert result.embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                texts=sample_texts,
                timeout=600_000,
            )

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_embed_texts_async__returns_embeddings_object__when_successful_AI(
        self, sample_embedding_data, sample_texts
    ):
        """
        Purpose: Verify that EmbeddingService.embed_texts_async returns a proper Embeddings object.
        Why this matters: Async service functionality for text embedding must work correctly.
        Setup summary: Mock async SDK response with sample embedding data.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")

        with patch.object(unique_sdk.Embeddings, "create_async") as mock_create:
            mock_create.return_value = sample_embedding_data

            # Act
            result = await service.embed_texts_async(sample_texts)

            # Assert
            assert isinstance(result, Embeddings)
            assert result.embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                texts=sample_texts,
                timeout=600_000,
            )

    @pytest.mark.ai_generated
    def test_embed_texts__raises_exception__when_sdk_error_AI(self, sample_texts):
        """
        Purpose: Verify that EmbeddingService.embed_texts properly propagates SDK errors.
        Why this matters: Error handling is critical for robust service functionality.
        Setup summary: Mock SDK to raise an exception.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")

        with patch.object(
            unique_sdk.Embeddings,
            "create",
            side_effect=Exception("API Error"),
        ):
            # Act & Assert
            with pytest.raises(Exception, match="API Error"):
                service.embed_texts(sample_texts)

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_embed_texts_async__raises_exception__when_sdk_error_AI(
        self, sample_texts
    ):
        """
        Purpose: Verify that EmbeddingService.embed_texts_async properly propagates SDK errors.
        Why this matters: Async error handling is critical for robust service functionality.
        Setup summary: Mock async SDK to raise an exception.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")

        with patch.object(
            unique_sdk.Embeddings,
            "create_async",
            side_effect=Exception("API Error"),
        ):
            # Act & Assert
            with pytest.raises(Exception, match="API Error"):
                await service.embed_texts_async(sample_texts)

    @pytest.mark.ai_generated
    def test_embedding_service__from_event__uses_correct_credentials_AI(
        self, base_chat_event
    ):
        """
        Purpose: Verify that EmbeddingService.from_event uses event credentials correctly.
        Why this matters: Event-based initialization must extract correct user and company IDs.
        Setup summary: Use base_chat_event fixture to test from_event classmethod.
        """
        # Arrange
        service = EmbeddingService.from_event(base_chat_event)

        with patch.object(unique_sdk.Embeddings, "create") as mock_create:
            mock_create.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

            # Act
            service.embed_texts(["test"])

            # Assert
            mock_create.assert_called_once_with(
                user_id=base_chat_event.user_id,
                company_id=base_chat_event.company_id,
                texts=["test"],
                timeout=600_000,
            )

    @pytest.mark.ai_generated
    def test_embedding_service__from_settings__uses_correct_credentials_AI(
        self, base_unique_settings
    ):
        """
        Purpose: Verify that EmbeddingService.from_settings uses settings credentials correctly.
        Why this matters: Settings-based initialization must extract correct user and company IDs.
        Setup summary: Use base_unique_settings fixture to test from_settings classmethod.
        """
        # Arrange
        service = EmbeddingService.from_settings(base_unique_settings)

        with patch.object(unique_sdk.Embeddings, "create") as mock_create:
            mock_create.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

            # Act
            service.embed_texts(["test"])

            # Assert
            mock_create.assert_called_once_with(
                user_id=base_unique_settings.auth.user_id.get_secret_value(),
                company_id=base_unique_settings.auth.company_id.get_secret_value(),
                texts=["test"],
                timeout=600_000,
            )
