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
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing_extensions import Self
from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.content.smart_rules import UniqueQL

RunResult = TypeVar("RunResult", bound=BaseModel, covariant=True)


class _ServiceBaseProtocol(Protocol, Generic[RunResult]):
    async def run(self) -> RunResult: ...

    """Runs the service with the prepared parameters."""


# What the space owner can change in the UI
Config = TypeVar("Config", bound=BaseModel)


class _ConfigMixingProtocol(Protocol, Generic[Config]):
    _config: Config

    @classmethod
    def from_config(cls, config: Config) -> Self: ...


# What can be changed via environment variables by admin
Settings = TypeVar("Settings", bound=BaseSettings, covariant=True)


class _SettingsMixingProtocol(Protocol, Generic[Settings]):
    _settings: Settings


Context = TypeVar("Context", bound=BaseModel)


class _ContextMixingProtocol(Protocol, Generic[Context]):
    _context: Context

    @property
    def context(self) -> Context: ...

    @context.setter
    def context(self, context: Context) -> None: ...


PrepareParameter = TypeVar("PrepareParameter", bound=BaseModel, contravariant=True)


# class PrepareMixingProtocol(Protocol, Generic[PrepareParameter]):
#    def prepare(self, parameter: PrepareParameter | dict) -> None: ...
#
#    """Prepares the service to be ran, resets the service to a clean state and inits parameters for run."""
#

ServiceState = TypeVar("ServiceState", bound=BaseModel)


class _StateMixingProtocol(Protocol, Generic[ServiceState]):
    _state: ServiceState

    @property
    def state(self) -> ServiceState: ...

    @state.setter
    def state(self, state: ServiceState) -> None: ...

    def reset_state(self) -> None: ...


ProgressMessage = TypeVar("ProgressMessage", bound=BaseModel | str)


class _ProgressMixingProtocol(Protocol, Generic[ProgressMessage]):
    _progress_publisher: TypedEventBus[ProgressMessage]

    @property
    def progress_publisher(self) -> TypedEventBus[ProgressMessage]: ...

    async def post_progress_message(self, message: ProgressMessage) -> None: ...


class PerfectServiceProtocol(
    _ServiceBaseProtocol, _StateMixingProtocol, _ProgressMixingProtocol
):
    pass

    # ------------------------------------------------------------ NEW File ------------------------------------------------------------
    pass


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


class InternalSearchServiceProtocol(
    _ServiceBaseProtocol[InternalSearchResult],
    _ConfigMixingProtocol[InternalSearchConfig],
    _StateMixingProtocol[InternalSearchState],
): ...


class InternalSearchService(InternalSearchServiceProtocol):
    def __init__(self, config: InternalSearchConfig, state: InternalSearchState):
        self._config = config
        self._state = state
        self._settings = InternalSearchSettings()

    @classmethod
    def from_config(
        cls, config: InternalSearchConfig, *, state: InternalSearchState | None = None
    ) -> Self:
        if state is None:
            state = InternalSearchState()

        return cls(config=config, state=state)

    @property
    def state(self) -> InternalSearchState:
        return self._state

    @state.setter
    def state(self, state: InternalSearchState) -> None:
        self._state = state

    async def run(self) -> InternalSearchResult:
        return InternalSearchResult()


def usage_example(internal_search_service: InternalSearchServiceProtocol) -> int:
    internal_search_service.state.search_queries.append("test")
    return 0


service = InternalSearchService.from_config(InternalSearchConfig())
usage_example(service)
