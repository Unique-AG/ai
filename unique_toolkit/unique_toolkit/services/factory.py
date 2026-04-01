from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Protocol, overload

from typing_extensions import Self, TypeVar

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.services.chat_service import ChatService
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

if TYPE_CHECKING:
    from unique_toolkit._common.chunk_relevancy_sorter.service import (
        ChunkRelevancySorter,
    )


class ServiceProtocol(Protocol):
    @classmethod
    def from_settings(cls, settings: UniqueSettings, **kwargs: Any) -> Self: ...


S = TypeVar("S", bound=ServiceProtocol)


class ServiceNotRegisteredError(Exception):
    """Raised when ``UniqueServiceFactory.create`` is called for an unregistered service type."""

    def __init__(self, service_type: type | str) -> None:
        name = service_type.__name__ if isinstance(service_type, type) else service_type
        super().__init__(
            f"Service '{name}' is not registered. "
            f"Use UniqueServiceFactory.register({name}, creator) to register it."
        )


class UniqueServiceFactory:
    """Registry-based factory for creating toolkit services from a :class:`UniqueSettings`.

    Can be used in two ways:

    **Class-level** — pass settings explicitly each time (good for one-off creation)::

        settings = UniqueSettings(auth=AuthContext(...), ...)

        svc = UniqueServiceFactory.create(ChatService, settings=settings)
        svc = UniqueServiceFactory.create("ChatService", settings=settings)  # string lookup

    **Instance-level** — bind settings once, create many services (good for handlers)::

        factory = UniqueServiceFactory(settings=settings)

        chat_svc = factory.chat_service()           # typed convenience method
        kb_svc   = factory.knowledge_base_service() # typed convenience method
        custom   = factory.get(MyCustomService)     # generic, for any registered service
    """

    _registry: ClassVar[dict[str, Callable[[UniqueSettings], ServiceProtocol]]] = {}

    # ── Bound (instance) factory ──────────────────────────────────────────────

    def __init__(self, *, settings: UniqueSettings) -> None:
        """Create a bound factory with pre-set settings.

        Args:
            settings: The settings shared by all services created from this instance.
        """
        self._settings = settings

    @overload
    def get(self, service_name: str, **kwargs: Any) -> ServiceProtocol: ...

    @overload
    def get(self, service_name: type[S], **kwargs: Any) -> S: ...

    def get(self, service_name: str | type[S], **kwargs: Any) -> ServiceProtocol | S:
        """Create a service using the pre-bound settings.

        Args:
            service_name: The registered name of the service to create.
            **kwargs: Additional keyword arguments forwarded to the creator.
        """
        service_creator: Callable[[UniqueSettings], ServiceProtocol] | None = None
        if isinstance(service_name, str):
            service_creator = self._registry.get(service_name, None)
        if isinstance(service_name, type):
            service_creator = self._registry.get(service_name.__name__, None)

        if service_creator is None:
            raise ServiceNotRegisteredError(service_name)

        return service_creator(self._settings, **kwargs)

    # ── Typed convenience methods (go through registry, respect overrides) ────

    def chat_service(self, **kwargs: Any) -> ChatService:
        """Create a :class:`ChatService` using the pre-bound context."""
        return self.get(ChatService, **kwargs)

    def knowledge_base_service(self, **kwargs: Any) -> KnowledgeBaseService:
        """Create a :class:`KnowledgeBaseService` using the pre-bound context."""
        return self.get(KnowledgeBaseService, **kwargs)

    def chunk_relevancy_sorter(self) -> ChunkRelevancySorter:
        """Create a :class:`ChunkRelevancySorter` using the pre-bound context."""
        from unique_toolkit._common.chunk_relevancy_sorter.service import (
            ChunkRelevancySorter,
        )

        return ChunkRelevancySorter.from_settings(self._settings)

    # ── Class-level registry operations ──────────────────────────────────────

    @classmethod
    def register(
        cls,
        service_class: type[ServiceProtocol],
    ) -> None:
        """Register a creator callable for *service_type*.

        Also registers the service under its string name (``service_type.__name__``
        by default, overridable via *name*) so it can be looked up with
        ``UniqueServiceFactory.create("ServiceName", ...)``.

        Overwrites any previously registered creator for the same type.

        Args:
            service_type: The service class to register.
            creator: A callable ``(settings: UniqueSettings, **kwargs) -> service_type``.
            name: Optional override for the string-lookup name. Defaults to
                ``service_type.__name__``.
        """
        cls._registry[service_class.__name__] = service_class.from_settings

    @classmethod
    def register_known_services(cls) -> None:
        """Register the default services with the factory.
        Currently only registers the KnowledgeBaseService and ChatService.
        """
        from unique_toolkit.services.chat_service import ChatService
        from unique_toolkit.services.knowledge_base import KnowledgeBaseService

        for service_class in [KnowledgeBaseService, ChatService]:
            if service_class.__name__ not in cls._registry:
                cls.register(service_class=service_class)

    @classmethod
    def create(
        cls,
        service_type: type[ServiceProtocol] | str,
        *,
        settings: Any,
        **kwargs: Any,
    ) -> ServiceProtocol:
        """Instantiate *service_type* using its registered creator.

        Accepts either the service class itself or its registered string name,
        so callers that don't want to import every service class can use strings.

        Args:
            service_type: The service class to instantiate, or its registered
                string name (e.g. ``"ChatService"``).
            settings: The context/settings object passed to the creator.
            **kwargs: Additional keyword arguments forwarded to the creator.

        Raises:
            ServiceNotRegisteredError: If *service_type* has not been registered.
        """
        key = service_type if isinstance(service_type, str) else service_type.__name__
        if key not in cls._registry:
            raise ServiceNotRegisteredError(service_type)
        return cls._registry[key](settings, **kwargs)

    @classmethod
    @contextmanager
    def override(
        cls,
        service_name: str | type,
        creator: Callable[..., Any],
    ) -> Generator[None, None, None]:
        """Context manager that temporarily replaces a service creator for testing.

        The original creator (or its absence) is restored when the block exits,
        even if an exception is raised.

        Args:
            service_name: The registered name (string) or class of the service to replace.
            creator: Replacement callable ``(settings, **kwargs) -> service_instance``.

        Example::

            mock_svc = MockChatService()
            with UniqueServiceFactory.override("ChatService", lambda settings, **kw: mock_svc):
                svc = UniqueServiceFactory.create(ChatService, settings=settings)
                assert svc is mock_svc
            # real creator is restored here
        """
        key = service_name if isinstance(service_name, str) else service_name.__name__
        previous = cls._registry.get(key, None)
        cls._registry[key] = creator
        try:
            yield
        finally:
            if previous is None:
                cls._registry.pop(key, None)
            else:
                cls._registry[key] = previous

    @classmethod
    def verify(cls, *service_names: str) -> None:
        """Assert that all given service types are registered.

        Call once at application startup to fail fast rather than discovering
        missing registrations on the first real request.

        Args:
            *service_names: Service names (strings) that must be registered.

        Raises:
            ServiceNotRegisteredError: For the first missing service type found.
        """
        for service_name in service_names:
            if service_name not in cls._registry:
                raise ServiceNotRegisteredError(service_name)
