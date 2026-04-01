from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing_extensions import Self
from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings

# ---------------------------------------------------------------------------
# Type variables
# ---------------------------------------------------------------------------

RunResult = TypeVar("RunResult", bound=BaseModel)
Config = TypeVar("Config", bound=BaseModel)
Settings = TypeVar("Settings", bound=BaseSettings)
Context = TypeVar("Context", bound=BaseModel)
ServiceState = TypeVar("ServiceState", bound=BaseModel)
ProgressMessage = TypeVar("ProgressMessage", bound=BaseModel | str)
Deps = TypeVar("Deps")


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class _RunMixin(ABC, Generic[RunResult]):
    """Service has a single entry point that returns a typed result."""

    @abstractmethod
    async def run(self) -> RunResult: ...


class _ConfigMixin(ABC, Generic[Config]):
    """Service is configurable from a space-owner Pydantic model.

    Subclasses must set ``_config_model_cls`` to the concrete Config type
    so that ``from_json`` can deserialize without requiring a subclass override.
    """

    _config_model_cls: type[Config]

    @classmethod
    @abstractmethod
    def from_config(cls, config: Config) -> Self: ...

    @property
    @abstractmethod
    def config(self) -> Config: ...

    @classmethod
    def from_json(cls, file_path: Path) -> Self:
        parsed = cls._config_model_cls.model_validate_json(file_path.read_text())
        return cls.from_config(parsed)


class _SettingsMixin(ABC, Generic[Settings]):
    """Service has immutable environment-variable settings loaded once at init."""

    @property
    @abstractmethod
    def settings(self) -> Settings: ...


class _ContextMixin(ABC, Generic[Context]):
    """Service holds a swappable request-scoped context (auth + optional chat).

    The context is set after construction (via ``bind_settings``) and can be
    replaced per request without rebuilding the service from scratch.
    """

    @property
    @abstractmethod
    def context(self) -> Context: ...

    @context.setter
    @abstractmethod
    def context(self, context: Context) -> None: ...


class _StateMixin(ABC, Generic[ServiceState]):
    """Service accumulates per-invocation state that is set before each ``run()``."""

    @property
    @abstractmethod
    def state(self) -> ServiceState: ...

    @state.setter
    @abstractmethod
    def state(self, state: ServiceState) -> None: ...

    @abstractmethod
    def reset_state(self) -> None: ...


class _ProgressMixin(Generic[ProgressMessage]):
    """Optional progress reporting via a typed event bus.

    Concrete by default — services that don't need progress reporting get a
    no-op bus without having to implement anything. Override
    ``post_progress_message`` for custom behaviour.
    """

    _progress_publisher: TypedEventBus[ProgressMessage]

    @property
    def progress_publisher(self) -> TypedEventBus[ProgressMessage]:
        if not hasattr(self, "_progress_publisher"):
            self._progress_publisher: TypedEventBus[ProgressMessage] = TypedEventBus()
        return self._progress_publisher

    async def post_progress_message(self, message: ProgressMessage) -> None:
        await self.progress_publisher.publish_and_wait_async(message)


class _DependenciesMixin(ABC, Generic[Deps]):
    """Service has injected services/deps

    Dependencies are set during ``bind_settings`` so the service doesn't
    construct them internally — making them easily replaceable in tests.
    """

    @property
    @abstractmethod
    def dependencies(self) -> Deps: ...

    @dependencies.setter
    @abstractmethod
    def dependencies(self, deps: Deps) -> None: ...


# ---------------------------------------------------------------------------
# BaseService
# ---------------------------------------------------------------------------


class BaseService(
    _RunMixin[RunResult],
    _ConfigMixin[Config],
    _ContextMixin[UniqueContext],
    _StateMixin[ServiceState],
    _ProgressMixin[ProgressMessage],
    _DependenciesMixin[Deps],
    Generic[RunResult, Config, ServiceState, ProgressMessage, Deps],
):
    """Convenience base that wires all mixins together.

    Initialization follows a two-step pattern that separates deployment-time
    config from request-time wiring:

     code-block:: python

        # Option A — one-shot (most common):
        service = MyService.from_settings(settings, config=my_config)

        # Option B — template pattern (startup once, bind per request):
        template = MyService.from_config(my_config)   # at startup
        service  = template.bind_settings(settings)   # per request

        # Option C — chatless (MCP, batch, no chat session):
        settings = UniqueSettings.from_env_auto_with_sdk_init()
        service  = MyService.from_settings(settings, config=my_config)
        # context.chat is None → no file scoping, no metadata filter from chat

    Subclasses must implement ``from_config`` and ``bind_settings``.
    ``from_settings`` is provided as a default that chains both.
    """

    @classmethod
    @abstractmethod
    def from_config(cls, config: Config) -> Self:
        """Config-only init (deployment-time). Call ``bind_settings`` before ``run``."""
        ...

    @abstractmethod
    def bind_settings(self, settings: UniqueSettings) -> Self:
        """Bind deps + context from settings (request-time). Returns self for chaining."""
        ...

    @classmethod
    def from_settings(cls, settings: UniqueSettings, **kwargs) -> Self:
        """Convenience: ``from_config(config).bind_settings(settings)``.

        Pass ``config`` as a keyword argument:
        ``MyService.from_settings(settings, config=my_config)``
        """
        config = kwargs.pop("config")
        return cls.from_config(config).bind_settings(settings)

    @cached_property
    def logger(self) -> logging.Logger:
        """Logger scoped to the concrete service class (e.g. ``unique_internal_search.service_v2.InternalSearchService``)."""
        return logging.getLogger(f"{type(self).__module__}.{type(self).__qualname__}")
