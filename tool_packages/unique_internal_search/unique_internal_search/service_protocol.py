from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing_extensions import Self
from unique_toolkit._common.event_bus import TypedEventBus

Config = TypeVar("Config", bound=BaseModel)
Settings = TypeVar("Settings", bound=BaseSettings, covariant=True)
PrepareParameter = TypeVar("PrepareParameter", bound=BaseModel, contravariant=True)
RunResult = TypeVar("RunResult", bound=BaseModel, covariant=True)


class ServiceProtocol(Protocol, Generic[Config, Settings, PrepareParameter, RunResult]):
    _config: Config
    _setting: Settings
    _progress_publisher: TypedEventBus[str] | None

    @classmethod
    def from_config(cls, config: Config) -> Self: ...

    def prepare(self, parameter: PrepareParameter | dict) -> None: ...

    """Prepares the service to be ran, resets the service to a clean state and inits parameters for run."""

    def reset(self) -> None: ...

    """Resets the service to a clean state as at configuration."""

    async def run(self) -> RunResult: ...

    """Runs the service with the prepared parameters."""
