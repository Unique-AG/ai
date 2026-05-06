import os
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.language_model import DEFAULT_LANGUAGE_MODEL

from unique_web_search.services.content_processing.processing_strategies.prompts import (
    DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE,
    DEFAULT_JUDGE_PROMPT_TEMPLATE,
    DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE,
    DEFAULT_PAGE_CONTEXT_TEMPLATE,
    DEFAULT_SANITIZE_RULES,
    DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    DEFAULT_USER_PROMPT_TEMPLATE,
)


class SanitizeMode(StrEnum):
    """Sanitization pipeline mode for privacy filtering."""

    ALWAYS_SANITIZE = "always_sanitize"
    JUDGE_ONLY = "judge_only"
    JUDGE_AND_SANITIZE = "judge_and_sanitize"
    JUDGE_THEN_SANITIZE = "judge_then_sanitize"
    KEYWORD_REDACT = "keyword_redact"

    @staticmethod
    def get_enum_names() -> list[str]:
        return [
            "Always Sanitize — summarize and redact every page unconditionally",
            "Judge Only — judge first; if flagged, replace content and snippet with a compliance notice",
            "Judge and Sanitize — single LLM call that judges and returns sanitized content when flagged",
            "Judge then Sanitize — judge first; if flagged, run a full summarize-and-sanitize call",
            "Keyword Redact — extract sensitive phrases and apply local regex replacement (no summarization)",
        ]


DEFAULT_FLAG_MESSAGE = (
    "THIS PAGE MAY CONTAIN SENSITIVE INFORMATION. "
    "ITS CONTENT HAS BEEN WITHHELD FOR COMPLIANCE REASONS. "
    "YOU CAN REFERENCE THE PAGE TO THE USER SO HE CAN EXPLORE THE CONTENT HIMSELF."
)


class PrivacyFilterEnvConfig(BaseModel):
    model_config = get_configuration_dict()

    sanitize: bool = False
    sanitize_mode: SanitizeMode = SanitizeMode.ALWAYS_SANITIZE
    flag_message: str = DEFAULT_FLAG_MESSAGE
    sanitize_rules: str = DEFAULT_SANITIZE_RULES


class PromptEnvConfig(BaseModel):
    model_config = get_configuration_dict()

    system_prompt: str = DEFAULT_SYSTEM_PROMPT_TEMPLATE
    user_prompt: str = DEFAULT_USER_PROMPT_TEMPLATE
    judge_prompt: str = DEFAULT_JUDGE_PROMPT_TEMPLATE
    judge_and_sanitize_prompt: str = DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE
    page_context_prompt: str = DEFAULT_PAGE_CONTEXT_TEMPLATE
    keyword_extract_prompt: str = DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE


class LLMProcessorEnvConfig(BaseModel):
    """Flat Pydantic model for the ``llm_process_config`` env-var JSON.

    Accepts both ``snake_case`` and ``camelCase`` keys thanks to the alias
    generator provided by ``get_configuration_dict``.  After construction,
    ``model_fields_set`` tells us which keys the IT admin explicitly provided
    so we can limit overrides to those fields only.
    """

    model_config = get_configuration_dict()

    enabled: bool = False
    language_model: Any = DEFAULT_LANGUAGE_MODEL
    min_tokens: int = 5000

    privacy_filter: PrivacyFilterEnvConfig = Field(
        default_factory=PrivacyFilterEnvConfig
    )

    prompts: PromptEnvConfig = Field(default_factory=PromptEnvConfig)


class ProcessingStrategiesSettings(BaseSettings):
    llm_processor_config: LLMProcessorEnvConfig = Field(
        default_factory=LLMProcessorEnvConfig
    )


class Settings(ProcessingStrategiesSettings):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / ".env", extra="ignore"
    )


class TestSettings(ProcessingStrategiesSettings):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / "tests/test.env", extra="ignore"
    )


def get_settings() -> ProcessingStrategiesSettings:
    """
    Dynamically load settings, switching to test environment if running under pytest.

    :return: Settings instance.
    """
    if "pytest" in sys.modules:
        # Dynamically adjust to use `test.env` if running under pytest
        return TestSettings()
    return Settings()


processing_strategies_settings: ProcessingStrategiesSettings = get_settings()
