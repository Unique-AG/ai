from unittest.mock import patch

import pytest
import unique_sdk

from tests.test_obj_factory import get_event_obj
from unique_toolkit.embedding.schemas import Embeddings
from unique_toolkit.embedding.service import EmbeddingService


class TestEmbeddingServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        # This method will be called before each test
        self.event = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )
        self.service = EmbeddingService(self.event)

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

    @pytest.mark.asyncio
    async def test_embed_texts_async(self):
        with patch.object(unique_sdk.Embeddings, "create_async") as mock_create:
            mock_create.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
            texts = ["Test text"]
            result = await self.service.embed_texts_async(texts)
            assert isinstance(result, Embeddings)
            assert result.embeddings == [[0.1, 0.2, 0.3]]
            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                texts=texts,
                timeout=600_000,
            )

    def test_error_handling_embed_texts(self):
        with patch.object(
            unique_sdk.Embeddings,
            "create",
            side_effect=Exception("API Error"),
        ):
            with pytest.raises(Exception, match="API Error"):
                self.service.embed_texts(["Test text"])

    @pytest.mark.asyncio
    async def test_error_handling_embed_texts_async(self):
        with patch.object(
            unique_sdk.Embeddings,
            "create_async",
            side_effect=Exception("API Error"),
        ):
            with pytest.raises(Exception, match="API Error"):
                await self.service.embed_texts_async(["Test text"])
