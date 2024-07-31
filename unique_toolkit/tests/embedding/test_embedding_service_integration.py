import pytest

from unique_toolkit.embedding.schemas import Embeddings
from unique_toolkit.embedding.service import EmbeddingService


@pytest.mark.usefixtures("chat_state")
class TestEmbeddingServiceIntegration:
    @pytest.fixture(autouse=True)
    def setup(self, chat_state):
        self.chat_state = chat_state
        self.service = EmbeddingService(self.chat_state)

    def test_embed_texts(self):
        texts = ["This is a test sentence.", "This is another test sentence."]
        result = self.service.embed_texts(texts)

        assert isinstance(result, Embeddings)
        assert len(result.embeddings) == len(texts)
        assert all(isinstance(embedding, list) for embedding in result.embeddings)
        assert all(
            isinstance(value, float)
            for embedding in result.embeddings
            for value in embedding
        )

    @pytest.mark.asyncio
    async def test_embed_texts_async(self):
        texts = ["This is a test sentence.", "This is another test sentence."]
        result = await self.service.embed_texts_async(texts)

        assert isinstance(result, Embeddings)
        assert len(result.embeddings) == len(texts)
        assert all(isinstance(embedding, list) for embedding in result.embeddings)
        assert all(
            isinstance(value, float)
            for embedding in result.embeddings
            for value in embedding
        )

    def test_get_cosine_similarity(self):
        texts = [
            "This is the first sentence.",
            "This is a completely different sentence.",
        ]
        embeddings = self.service.embed_texts(texts)

        similarity = self.service.get_cosine_similarity(
            embeddings.embeddings[0], embeddings.embeddings[1]
        )

        assert isinstance(similarity, float)
        assert 0 <= similarity <= 1  # Cosine similarity is always between 0 and 1

    def test_embed_texts_error_handling(self):
        with pytest.raises(Exception):
            self.service.embed_texts([""] * 1000)

    @pytest.mark.asyncio
    async def test_embed_texts_error_handling_async(self):
        with pytest.raises(Exception):
            await self.service.embed_texts_async([""] * 1000)

    def test_embed_texts_consistency(self):
        text = "This is a test sentence for consistency."
        result1 = self.service.embed_texts([text])
        result2 = self.service.embed_texts([text])

        assert (
            result1.embeddings == result2.embeddings
        ), "Embeddings should be consistent for the same text"
