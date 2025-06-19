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
            self._company_id: str = event.company_id
            self._user_id: str = event.user_id
        else:
            [company_id, user_id] = validate_required_values([company_id, user_id])
            self._company_id: str = company_id
            self._user_id: str = user_id

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

    @property
    @deprecated(
        "The company_id property is deprecated and will be removed in a future version."
    )
    def company_id(self) -> str | None:
        """
        Get the company identifier (deprecated).

        Returns:
            str | None: The company identifier.
        """
        return self._company_id

    @company_id.setter
    @deprecated(
        "The company_id setter is deprecated and will be removed in a future version."
    )
    def company_id(self, value: str) -> None:
        """
        Set the company identifier (deprecated).

        Args:
            value (str | None): The company identifier.
        """
        self._company_id = value

    @property
    @deprecated(
        "The user_id property is deprecated and will be removed in a future version."
    )
    def user_id(self) -> str | None:
        """
        Get the user identifier (deprecated).

        Returns:
            str | None: The user identifier.
        """
        return self._user_id

    @user_id.setter
    @deprecated(
        "The user_id setter is deprecated and will be removed in a future version."
    )
    def user_id(self, value: str) -> None:
        """
        Set the user identifier (deprecated).

        Args:
            value (str | None): The user identifier.
        """
        self._user_id = value

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
            user_id=self._user_id,
            company_id=self._company_id,
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
            user_id=self._user_id,
            company_id=self._company_id,
            texts=texts,
            timeout=timeout,
        )
