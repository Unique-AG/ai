import os
import sys
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_search_proxy_core.agent_engines.bing.enums import BingMarket

_ENV_PREFIX = "BING_AGENT_"


class _BingAgentEnvSettings(BaseSettings):
    default_market: BingMarket | None = Field(
        default=None,
        description=(
            "Bing market applied to grounded searches whose space leaves "
            "Market blank. Unset means no market is sent at all."
        ),
    )

    @field_validator("default_market", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: Any) -> Any:
        """Treat an empty variable as unset instead of failing to boot.

        Helm renders an unconfigured optional value as ``""``, which
        ``BingMarket`` would reject. A non-blank typo still fails at startup.
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value


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


def resolve_market(value: str | None = None) -> str | None:
    """Return the market to send to Bing, or ``None`` to send none at all.

    The space's fixed market wins, falling back to ``BING_AGENT_DEFAULT_MARKET``.
    With neither set, ``mkt`` is left off the grounding tool entirely.
    """
    return value or bing_agent_env_settings.default_market
