import os
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Base(BaseSettings):
    input_correction_reduction_factor: float = Field(
        default=0.1,
        ge=0.0,
        lt=1.0,
        description="The factor by which the input tokens will be reduced.",
    )
    input_aggressive_reduction_factor: float = Field(
        default=0.9,
        ge=0.0,
        lt=1.0,
        description="The safety margin for the input correction.",
    )


def get_model_config(test: bool = False) -> SettingsConfigDict:
    if test:
        env_file = Path(os.getcwd()) / "tests/test.env"
    else:
        env_file = Path(os.getcwd()) / ".env"

    return SettingsConfigDict(
        extra="ignore",
        env_prefix="TOOLKIT_HISTORY_MANAGER_",
        case_sensitive=False,
        env_file=env_file,
        env_file_encoding="utf-8",
    )


class Settings(Base):
    model_config = get_model_config()


class TestSettings(Base):
    model_config = get_model_config(test=True)


def get_settings() -> Base:
    if "pytest" in sys.modules:
        return TestSettings()
    return Settings()


env_settings: Base = get_settings()
