from unittest.mock import Mock, patch

import pytest
import unique_sdk

from unique_toolkit.chat.state import ChatState
from unique_toolkit.embedding.schemas import Embeddings
from unique_toolkit.embedding.service import EmbeddingService


class TestEmbeddingServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        # This method will be called before each test
        self.chat_state = ChatState(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )
        self.service = EmbeddingService(self.chat_state)

    def test_embed_texts(self):
        with patch.object(unique_sdk.Embeddings, "create") as mock_create:
            mock_create.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
            texts = ["Test text"]
            result = self.service.embed_texts(texts)
            assert isinstance(result, Embeddings)
            assert result.embeddings == [[0.1, 0.2, 0.3]]
            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                texts=texts,
                timeout=600_000,
            )

    def test_trigger_embed_texts(self):
        with patch.object(unique_sdk.Embeddings, "create") as mock_create:
            mock_create.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
            texts = ["Test text"]
            result = self.service._trigger_embed_texts(texts, 600_000)
            assert isinstance(result, Embeddings)
            assert result.embeddings == [[0.1, 0.2, 0.3]]
            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                texts=texts,
                timeout=600_000,
            )

    def test_get_cosine_similarity(self):
        embedding_1 = [1.0, 0.0, 1.0]
        embedding_2 = [0.0, 1.0, 0.0]
        result = self.service.get_cosine_similarity(embedding_1, embedding_2)
        expected = 0  # Orthogonal vectors have cosine similarity of 0
        assert pytest.approx(result) == expected

        embedding_1 = [1.0, 1.0, 1.0]
        embedding_2 = [1.0, 1.0, 1.0]
        result = self.service.get_cosine_similarity(embedding_1, embedding_2)
        expected = 1  # Identical vectors have cosine similarity of 1
        assert pytest.approx(result) == expected

    def test_init_with_logger(self):
        logger = Mock()
        service = EmbeddingService(self.chat_state, logger)
        assert service.logger == logger

    def test_init_without_logger(self):
        service = EmbeddingService(self.chat_state)
        assert service.logger is not None

    def test_error_handling_search_contents(self):
        with patch.object(
            unique_sdk.Embeddings,
            "create",
            side_effect=Exception("API Error"),
        ):
            with pytest.raises(Exception, match="API Error"):
                self.service.embed_texts(["Test text"])
