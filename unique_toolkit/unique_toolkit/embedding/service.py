from typing_extensions import deprecated

from unique_toolkit._common._base_service import BaseService
from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import BaseEvent, Event
from unique_toolkit.embedding.constants import DEFAULT_TIMEOUT
from unique_toolkit.embedding.functions import embed_texts, embed_texts_async
from unique_toolkit.embedding.schemas import Embeddings


class EmbeddingService(BaseService):
    """
    Provides methods to interact with the Embedding service.

    Attributes:
        company_id (str | None): The company ID.
        user_id (str | None): The user ID.
    """

    def __init__(
        self,
        event: Event | BaseEvent | None = None,
        company_id: str | None = None,
        user_id: str | None = None,
    ):
        self._event = event
        if event:
            self.company_id = event.company_id
            self.user_id = event.user_id
        else:
            [company_id, user_id] = validate_required_values([company_id, user_id])
            self.company_id = company_id
            self.user_id = user_id

    @property
    @deprecated(
        "The event property is deprecated and will be removed in a future version."
    )
    def event(self) -> Event | BaseEvent | None:
        """
        Get the event object (deprecated).

        Returns:
            Event | BaseEvent | None: The event object.
        """
        return self._event

    def embed_texts(
        self,
        texts: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Embeddings:
        """
        Embed text.

        Args:
            text (str): The text to embed.
            timeout (int): The timeout in milliseconds. Defaults to 600000.

        Returns:
            Embeddings: The Embedding object.

        Raises:
            Exception: If an error occurs.
        """
        return embed_texts(
            user_id=self.user_id,
            company_id=self.company_id,
            texts=texts,
            timeout=timeout,
        )

    async def embed_texts_async(
        self,
        texts: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Embeddings:
        """
        Embed text asynchronously.

        Args:
            text (str): The text to embed.
            timeout (int): The timeout in milliseconds. Defaults to 600000.

        Returns:
            Embeddings: The Embedding object.

        Raises:
            Exception: If an error occurs.
        """
        return await embed_texts_async(
            user_id=self.user_id,
            company_id=self.company_id,
            texts=texts,
            timeout=timeout,
        )
