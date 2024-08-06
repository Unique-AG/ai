import logging
from typing import Optional

import unique_sdk

from unique_toolkit._common._base_service import BaseService
from unique_toolkit.chat.state import ChatState
from unique_toolkit.embedding.schemas import Embeddings


class EmbeddingService(BaseService):
    """
    Provides methods to interact with the Embedding service.

    Attributes:
        state (ChatState): The ChatState object.
        logger (Optional[logging.Logger]): The logger object. Defaults t∏o None.
    """

    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        super().__init__(state, logger)

    DEFAULT_TIMEOUT = 600_000

    def embed_texts(
        self,
        texts: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Embeddings:
        """
        Embed text.

        Args:
            text (str): The text to embed.
            timeout (int): The timeout in milliseconds. Defaults to None.

        Returns:
            Embeddings: The Embedding object.

        Raises:
            Exception: If an error occurs.
        """
        request = self._get_request_obj(texts=texts, timeout=timeout)
        try:
            response = unique_sdk.Embeddings.create(**request)
            return Embeddings(**response)
        except Exception as e:
            self.logger.error(f"Error embedding texts: {e}")
            raise e

    async def embed_texts_async(
        self,
        texts: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Embeddings:
        """
        Embed text asynchronously.

        Args:
            text (str): The text to embed.
            timeout (int): The timeout in milliseconds. Defaults to None.

        Returns:
            Embeddings: The Embedding object.

        Raises:
            Exception: If an error occurs.
        """
        request = self._get_request_obj(texts=texts, timeout=timeout)
        try:
            response = await unique_sdk.Embeddings.create_async(**request)
            return Embeddings(**response)
        except Exception as e:
            self.logger.error(f"Error embedding texts: {e}")
            raise e

    def _get_request_obj(self, texts: list[str], timeout: int) -> dict:
        return {
            "user_id": self.state.user_id,
            "company_id": self.state.company_id,
            "texts": texts,
            "timeout": timeout,
        }
