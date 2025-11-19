import base64
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
    quartr_api_creds: str | None = None
    quartr_api_activated_companies: list[str] = []

    @property
    def quartr_api_creds_model(self) -> QuartrApiCreds | None:
        """Return the Quartr API credentials model."""
        if self.quartr_api_creds is None:
            return None

        decoded_creds = base64.b64decode(self.quartr_api_creds).decode("utf-8")
        return QuartrApiCreds.model_validate_json(decoded_creds)


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
