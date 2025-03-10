import pytest

from unique_sdk.api_resources._embedding import Embeddings


@pytest.mark.integration
class TestEmbeddings:
    def test_create_embeddings(self, event):
        """Test creating embeddings synchronously in sandbox."""
        texts = ["Hello world", "Test embedding"]

        response = Embeddings.create(
            user_id=event.user_id, company_id=event.company_id, texts=texts
        )

        assert isinstance(response.embeddings, list)
        assert len(response.embeddings) == len(texts)
        # Each embedding should be a list of floats
        for embedding in response.embeddings:
            assert isinstance(embedding, list)
            assert all(isinstance(x, float) for x in embedding)
            # Typical embedding dimensions (e.g., 1536 for GPT models)
            assert len(embedding) > 0

    @pytest.mark.asyncio
    async def test_create_embeddings_async(self, event):
        """Test creating embeddings asynchronously in sandbox."""
        texts = ["Hello world async", "Test embedding async"]

        response = await Embeddings.create_async(
            user_id=event.user_id, company_id=event.company_id, texts=texts
        )

        assert isinstance(response.embeddings, list)
        assert len(response.embeddings) == len(texts)
        # Each embedding should be a list of floats
        for embedding in response.embeddings:
            assert isinstance(embedding, list)
            assert all(isinstance(x, float) for x in embedding)
            # Typical embedding dimensions (e.g., 1536 for GPT models)
            assert len(embedding) > 0
