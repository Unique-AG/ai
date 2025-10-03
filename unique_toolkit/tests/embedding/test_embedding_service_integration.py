import pytest

from unique_toolkit.embedding.schemas import Embeddings
from unique_toolkit.embedding.service import EmbeddingService


@pytest.fixture
def sample_texts():
    """Sample texts for embedding integration tests."""
    return ["This is a test sentence.", "This is another test sentence."]


@pytest.fixture
def large_text_list():
    """Large list of texts to test error handling."""
    return [""] * 1000


class TestEmbeddingServiceIntegration:
    @pytest.mark.ai_generated
    def test_embed_texts__returns_valid_embeddings__when_integration_successful_AI(
        self, sample_texts
    ):
        """
        Purpose: Verify that EmbeddingService.embed_texts works with real API integration.
        Why this matters: Integration testing ensures the service works with actual API calls.
        Setup summary: Use real service with sample texts for integration testing.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")

        # Act
        result = service.embed_texts(sample_texts)

        # Assert
        assert isinstance(result, Embeddings)
        assert len(result.embeddings) == len(sample_texts)
        assert all(isinstance(embedding, list) for embedding in result.embeddings)
        assert all(
            isinstance(value, float)
            for embedding in result.embeddings
            for value in embedding
        )

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_embed_texts_async__returns_valid_embeddings__when_integration_successful_AI(
        self, sample_texts
    ):
        """
        Purpose: Verify that EmbeddingService.embed_texts_async works with real API integration.
        Why this matters: Async integration testing ensures the service works with actual API calls.
        Setup summary: Use real async service with sample texts for integration testing.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")

        # Act
        result = await service.embed_texts_async(sample_texts)

        # Assert
        assert isinstance(result, Embeddings)
        assert len(result.embeddings) == len(sample_texts)
        assert all(isinstance(embedding, list) for embedding in result.embeddings)
        assert all(
            isinstance(value, float)
            for embedding in result.embeddings
            for value in embedding
        )

    @pytest.mark.ai_generated
    def test_embed_texts__raises_exception__when_large_input_AI(self, large_text_list):
        """
        Purpose: Verify that EmbeddingService.embed_texts handles large inputs appropriately.
        Why this matters: Error handling for edge cases ensures robust service functionality.
        Setup summary: Use large text list to trigger error conditions.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")

        # Act & Assert
        with pytest.raises(Exception):
            service.embed_texts(large_text_list)

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_embed_texts_async__raises_exception__when_large_input_AI(
        self, large_text_list
    ):
        """
        Purpose: Verify that EmbeddingService.embed_texts_async handles large inputs appropriately.
        Why this matters: Async error handling for edge cases ensures robust service functionality.
        Setup summary: Use large text list to trigger error conditions.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")

        # Act & Assert
        with pytest.raises(Exception):
            await service.embed_texts_async(large_text_list)

    @pytest.mark.ai_generated
    def test_embed_texts__returns_consistent_embeddings__when_same_text_AI(self):
        """
        Purpose: Verify that EmbeddingService.embed_texts returns consistent embeddings for the same text.
        Why this matters: Consistency is critical for embedding functionality to be reliable.
        Setup summary: Use same text multiple times to verify consistency.
        """
        # Arrange
        service = EmbeddingService(company_id="test_company", user_id="test_user")
        text = "This is a test sentence for consistency."

        # Act
        result1 = service.embed_texts([text])
        result2 = service.embed_texts([text])

        # Assert
        assert result1.embeddings == result2.embeddings, (
            "Embeddings should be consistent for the same text"
        )
