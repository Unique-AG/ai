import os
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PREFIX = "BING_AGENT_"


class _BingAgentEnvSettings(BaseSettings):
    default_market: str | None = Field(
        default=None,
        description="Default Bing market for grounded searches",
    )


def _get_settings() -> _BingAgentEnvSettings:
    if "pytest" in sys.modules:
        env_file = Path(os.getcwd()) / "tests/test.env"
    else:
        env_file = Path(os.getcwd()) / ".env"

    class _Settings(_BingAgentEnvSettings):
        model_config = SettingsConfigDict(
            env_file=env_file,
            env_prefix=_ENV_PREFIX,
            extra="ignore",
        )

    return _Settings()


bing_agent_env_settings = _get_settings()
