from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel
from typing_extensions import Self

from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings

RunResult = TypeVar("RunResult", bound=BaseModel)
Config = TypeVar("Config", bound=BaseModel)
Context = TypeVar("Context")
ServiceState = TypeVar("ServiceState")
ProgressMessage = TypeVar("ProgressMessage")
Deps = TypeVar("Deps")


class _RunMixin(ABC, Generic[RunResult]):
    @abstractmethod
    async def run(self) -> RunResult: ...


class _ConfigMixin(ABC, Generic[Config]):
    """Subclasses must set ``_config_model_cls`` so ``from_json`` can deserialize."""

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


class _ContextMixin(ABC, Generic[Context]):
    @property
    @abstractmethod
    def context(self) -> Context: ...


class _StateMixin(ABC, Generic[ServiceState]):
    @property
    @abstractmethod
    def state(self) -> ServiceState: ...

    @abstractmethod
    def reset_state(self) -> None: ...


class _ProgressMixin(Generic[ProgressMessage]):
    """Concrete by default — no-op bus unless something subscribes."""

    def __init__(self) -> None:
        super().__init__()
        self._progress_publisher: TypedEventBus[ProgressMessage] = TypedEventBus()

    @property
    def progress_publisher(self) -> TypedEventBus[ProgressMessage]:
        return self._progress_publisher

    async def post_progress_message(self, message: ProgressMessage) -> None:
        await self.progress_publisher.publish_and_wait_async(message)


class _DependenciesMixin(ABC, Generic[Deps]):
    @property
    @abstractmethod
    def dependencies(self) -> Deps: ...


class BaseService(  # pyright: ignore[reportImplicitAbstractClass]
    _RunMixin[RunResult],
    _ConfigMixin[Config],
    _ContextMixin[UniqueContext],
    _StateMixin[ServiceState],
    _ProgressMixin[ProgressMessage],
    _DependenciesMixin[Deps],
    Generic[RunResult, Config, ServiceState, ProgressMessage, Deps],
):
    """
    Two-step init: from_config() at startup, bind_settings() per request.

        service = MyService.from_config(config)      # startup
        service = service.bind_settings(settings)    # per request
        # or in one shot:
        service = MyService.from_settings(settings, config=config)
    """

    _config: Config
    _context: UniqueContext
    _state: ServiceState
    _dependencies: Deps

    @abstractmethod
    def bind_settings(self, settings: UniqueSettings) -> Self: ...

    @classmethod
    def from_settings(cls, settings: UniqueSettings, **kwargs) -> Self:
        config = kwargs.pop("config")
        return cls.from_config(config).bind_settings(settings)

    @property
    def config(self) -> Config:
        return self._config  # type: ignore[attr-defined]

    @property
    def context(self) -> UniqueContext:
        return self._context  # type: ignore[attr-defined]

    @context.setter
    def context(self, context: UniqueContext) -> None:
        self._context = context

    @property
    def state(self) -> ServiceState:
        return self._state  # type: ignore[attr-defined]

    @state.setter
    def state(self, state: ServiceState) -> None:
        self._state = state

    @property
    def dependencies(self) -> Deps:
        return self._dependencies  # type: ignore[attr-defined]

    @dependencies.setter
    def dependencies(self, deps: Deps) -> None:
        self._dependencies = deps

    @cached_property
    def logger(self) -> logging.Logger:
        return logging.getLogger(f"{type(self).__module__}.{type(self).__qualname__}")


__all__ = ["BaseService"]
