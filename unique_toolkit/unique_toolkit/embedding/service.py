from typing import overload

from typing_extensions import deprecated

from unique_toolkit._common._base_service import BaseService
from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import BaseEvent, Event
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.embedding.constants import DEFAULT_TIMEOUT
from unique_toolkit.embedding.functions import embed_texts, embed_texts_async
from unique_toolkit.embedding.schemas import Embeddings


class EmbeddingService(BaseService):
    """
    Provides methods to interact with the Embedding service.
    """

    @deprecated(
        "Use __init__ with company_id and user_id instead or use the classmethod `from_event`"
    )
    @overload
    def __init__(self, event: Event | BaseEvent): ...

    """
        Initialize the EmbeddingService with an event (deprecated)
    """

    @overload
    def __init__(self, *, company_id: str, user_id: str): ...

    """
        Initialize the EmbeddingService with a company_id and user_id.
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

    @classmethod
    def from_event(cls, event: Event | BaseEvent):
        """
        Initialize the EmbeddingService with an event.
        """
        return cls(company_id=event.company_id, user_id=event.user_id)

    @classmethod
    def from_settings(cls, settings: UniqueSettings | str | None = None):
        """
        Initialize the EmbeddingService with a settings object.
        """

        if settings is None:
            settings = UniqueSettings.from_env_auto_with_sdk_init()
        elif isinstance(settings, str):
            settings = UniqueSettings.from_env_auto_with_sdk_init(filename=settings)

        return cls(
            company_id=settings.auth.company_id.get_secret_value(),
            user_id=settings.auth.user_id.get_secret_value(),
        )

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

    @deprecated(
        "Use keyword only method instead. Positional arguments are deprecated and will be removed on the 1st of January 2026."
    )
    @overload
    def embed_texts(
        self,
        texts: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Embeddings: ...

    @overload
    def embed_texts(  # type: ignore
        self,
        *,
        texts: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Embeddings: ...

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

    @deprecated(
        "Use keyword only method instead. Positional arguments are deprecated and will be removed on the 1st of January 2026."
    )
    @overload
    async def embed_texts_async(
        self,
        texts: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Embeddings: ...

    @overload
    async def embed_texts_async(  # type: ignore
        self,
        *,
        texts: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Embeddings: ...

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
