import os
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelFamily(StrEnum):
    """Model lineage / who built the model.

    Distinct from ``LanguageModelProvider`` (AZURE / LITELLM / CUSTOM), which
    describes how the model is served. A Claude on Vertex and a Claude on
    Anthropic share the same family but have different providers.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    MISTRAL = "mistral"
    ZAI = "zai"
    UNKNOWN = "unknown"


class Base(BaseSettings):
    token_limit_multiplier: dict[ModelFamily, float] = Field(
        default={
            ModelFamily.ANTHROPIC: 0.75,
        },
    )


def get_model_config(test: bool = False) -> SettingsConfigDict:
    if test:
        env_file = Path(os.getcwd()) / "tests/test.env"
    else:
        env_file = Path(os.getcwd()) / ".env"

    return SettingsConfigDict(
        extra="ignore",
        env_prefix="TOOLKIT_LANGUAGE_MODEL_",
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
