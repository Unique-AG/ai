import logging
from typing import Optional

import numpy as np
import unique_sdk

from unique_toolkit.chat.state import ChatState
from unique_toolkit.embedding.schema import Embeddings
from unique_toolkit.performance.async_wrapper import async_warning, to_async


class EmbeddingService:
    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        self.state = state
        self.logger = logger or logging.getLogger(__name__)

    _DEFAULT_TIMEOUT = 600_000

    def embed_texts(self, texts: list[str], timeout: int = 600_000) -> Embeddings:
        """
        Embed text.

        Args:
            text (str): The text to embed.

        Returns:
            Embeddings: The Embedding object.
        """
        return self._trigger_embed_texts(texts, timeout)

    @to_async
    @async_warning
    def async_embed_texts(
        self,
        texts: list[str],
        timeout: int,
    ) -> Embeddings:
        """
        Embed text asynchronously.

        Args:
            text (str): The text to embed.

        Returns:
            Embeddings: The Embedding object.
        """
        return self._trigger_embed_texts(texts, timeout)

    def _trigger_embed_texts(
        self,
        texts: list[str],
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> Embeddings:
        request = {
            "user_id": self.state.user_id,
            "company_id": self.state.company_id,
            "texts": [texts],
            "timeout": timeout,
        }
        response = unique_sdk.Embeddings.create(**request)
        return Embeddings(**response)

    def get_cosine_similarity(
        self,
        embedding_1: list[float],
        embedding_2: list[float],
    ) -> float:
        """Get cosine similarity."""
        return np.dot(embedding_1, embedding_2) / (
            np.linalg.norm(embedding_1) * np.linalg.norm(embedding_2)
        )
