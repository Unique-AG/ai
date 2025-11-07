import os
import sys
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class QuartrApiCreds(BaseModel):
    model_config = get_configuration_dict()

    api_key: str
    valid_to: str


class Base(BaseSettings):
    quartr_api_creds: QuartrApiCreds | None = None
    quartr_api_activated_companies: list[str] = []


class Settings(Base):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / ".env", extra="ignore"
    )


class TestSettings(Base):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / "tests/test.env", extra="ignore"
    )


def get_settings() -> Base:
    """
    Dynamically load settings, switching to test environment if running under pytest.

    :return: Settings instance.
    """
    if "pytest" in sys.modules:
        # Dynamically adjust to use `test.env` if running under pytest
        return TestSettings()
    return Settings()


quartr_settings: Base = get_settings()
