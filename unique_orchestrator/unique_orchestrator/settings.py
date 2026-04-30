"""Runtime settings for the ``unique_orchestrator`` package.

This module centralizes the orchestrator's configurable knobs and exposes a
single, lazily-loaded ``env_settings`` instance for the rest of the package
to consume.

Responsibilities:
    * Define the ``Base`` settings schema (loop/tool-call limits and the
      warning message shown when the language model returns no output).
    * Source values from environment variables (prefixed with
      ``UNIQUE_ORCHESTRATOR_``) and from a ``.env`` file resolved relative
      to the current working directory.
    * Transparently switch to ``tests/test.env`` when the process is being
      executed under ``pytest``, so tests get a deterministic configuration
      without changes at the call site.

Typical usage:
    >>> from unique_orchestrator.settings import env_settings
    >>> env_settings.limit_max_loop_iterations
    100
"""

import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EMPTY_MESSAGE_WARNING = (
    "⚠️ **The language model was unable to produce an output.**\n"
    "It did not generate any content or perform a tool call in response to your request. "
    "This is a limitation of the language model itself.\n\n"
    "**Please try adapting or simplifying your prompt.** "
    "Rewording your input can often help the model respond successfully."
)


class Base(BaseSettings):
    empty_message_warning: str = Field(
        default=EMPTY_MESSAGE_WARNING,
        description="The warning message to display when the language model is unable to produce an output.",
    )

    limit_max_loop_iterations: int = Field(
        default=100,
        description="The maximum number of loop iterations to allow.",
    )

    limit_max_tool_calls_per_iteration: int = Field(
        default=50,
        description="The maximum number of tool calls to allow per iteration.",
    )


def get_model_config(env: Literal["test", "dev"] = "dev") -> SettingsConfigDict:
    base_path = Path(os.getcwd())
    
    if env == "test":
        env_file = base_path / "tests/test.env"
    else:
        env_file = base_path / ".env"

    return SettingsConfigDict(
        extra="ignore",
        env_prefix="UNIQUE_ORCHESTRATOR_",
        case_sensitive=False,
        env_file=env_file,
        env_file_encoding="utf-8",
    )


class Settings(Base):
    model_config = get_model_config()


class TestSettings(Base):
    model_config = get_model_config(env="test")


def get_settings() -> Base:
    """
    Dynamically load settings, switching to test environment if running under pytest.

    :return: Settings instance.
    """
    if "pytest" in sys.modules:
        # Dynamically adjust to use `test.env` if running under pytest
        return TestSettings()
    return Settings()


env_settings: Base = get_settings()
