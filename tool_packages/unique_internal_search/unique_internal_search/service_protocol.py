# Reasoning
#
# A base service should have:
# - A configuration that can be changed at runtime -> pydantic model
# - A settings that is constant after init -> environment variables -> pydantic settings
# - A service should have a clear goal -> Result after run -> pydantic model
# - A service should have a clear interface -> dataclass (and maybe derived pydantic model)
# - A service initializable from config only?
# - A service should be resetable to a clean state as at initialization
#


# All methods asynd or not? MCP is all async, maybe run method should be async?
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing_extensions import Self
from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.content.smart_rules import UniqueQL

RunResult = TypeVar("RunResult", bound=BaseModel, covariant=True)


class _RunMixing(ABC, Generic[RunResult]):
    @abstractmethod
    async def run(self) -> RunResult: ...

    """Runs the service with the prepared parameters."""


# What the space owner can change in the UI
Config = TypeVar("Config", bound=BaseModel)


class _ConfigMixing(ABC, Generic[Config]):
    """Subclasses must set ``_config_model_cls`` to the concrete Pydantic model type."""

    # TODO: Talk to Ahmed about this
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


# What can be changed via environment variables by admin
Settings = TypeVar("Settings", bound=BaseSettings, covariant=True)


class _SettingsMixing(ABC, Generic[Settings]):
    @property
    @abstractmethod
    def settings(self) -> Settings: ...


Context = TypeVar("Context", bound=BaseModel)


class _ContextMixing(ABC, Generic[Context]):
    @property
    @abstractmethod
    def context(self) -> Context: ...

    @context.setter
    @abstractmethod
    def context(self, context: Context) -> None: ...


ServiceState = TypeVar("ServiceState", bound=BaseModel)


class _StateMixing(ABC, Generic[ServiceState]):
    @property
    @abstractmethod
    def state(self) -> ServiceState: ...

    @state.setter
    @abstractmethod
    def state(self, state: ServiceState) -> None: ...

    @abstractmethod
    def reset_state(self) -> None: ...


ProgressMessage = TypeVar("ProgressMessage", bound=BaseModel | str)


class _ProgressMixing(ABC, Generic[ProgressMessage]):
    _progress_publisher: TypedEventBus[ProgressMessage]

    @property
    def progress_publisher(self) -> TypedEventBus[ProgressMessage]: ...

    async def post_progress_message(self, message: ProgressMessage) -> None: ...


class BaseService(
    _RunMixing, _SettingsMixing, _ConfigMixing, _StateMixing, _ProgressMixing
):
    pass

    # ------------------------------------------------------------ NEW File ------------------------------------------------------------


class InternalSearchSettings(BaseSettings):
    pass


class InternalSearchConfig(BaseModel):
    max_search_strings: int = Field(default=10)
    metadata_filter: UniqueQL | None = Field(default=None)


class InternalSearchResult(BaseModel):
    content_chunks: list[ContentChunk] = Field(default=[])


class InternalSearchState(BaseModel):
    search_queries: list[str] = Field(default=[])
    content_ids: list[str] = Field(default=[])
    metadata_filter_override: UniqueQL | None = Field(default=None)


class InternalSearchServiceAbstract(
    _RunMixing[InternalSearchResult],
    _SettingsMixing[InternalSearchSettings],
    _ConfigMixing[InternalSearchConfig],
    _StateMixing[InternalSearchState],
):
    _config_model_cls: type[InternalSearchConfig] = InternalSearchConfig


class InternalSearchService(InternalSearchServiceAbstract):
    def __init__(self, config: InternalSearchConfig, state: InternalSearchState):
        self._config = config
        self._state = state
        self._settings = InternalSearchSettings()

    @property
    def config(self) -> InternalSearchConfig:
        return self._config

    @property
    def settings(self) -> InternalSearchSettings:
        return self._settings

    @classmethod
    def from_config(cls, config: InternalSearchConfig) -> Self:
        state = InternalSearchState()
        return cls(config=config, state=state)

    @property
    def state(self) -> InternalSearchState:
        return self._state

    @state.setter
    def state(self, state: InternalSearchState) -> None:
        self._state = state

    def reset_state(self) -> None:
        self._state = InternalSearchState()

    async def run(self) -> InternalSearchResult:
        return InternalSearchResult()


if __name__ == "__main__":
    import asyncio

    async def main():
        service = InternalSearchService(
            config=InternalSearchConfig(), state=InternalSearchState()
        )
        await service.run()

    asyncio.run(main())
