from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TypeVar, cast

from pydantic_settings import BaseSettings, SettingsConfigDict

T = TypeVar("T", bound=BaseSettings)


def _get_env_path(*, test: bool = False) -> Path:
    return Path(os.getcwd()) / ("tests/test.env" if test else ".env")


def _settings_config(
    *,
    env_prefix: str = "",
    test: bool = False,
) -> SettingsConfigDict:
    env_file = _get_env_path(test=test)
    return SettingsConfigDict(
        extra="ignore",
        env_prefix=env_prefix,
        case_sensitive=False,
        env_file=env_file,
        env_file_encoding="utf-8",
        frozen=True,
    )


def _is_test_runtime() -> bool:
    return "pytest" in sys.modules


def get_settings(cls: type[T], *, env_prefix: str) -> T:
    """Load a settings model from env; uses ``tests/test.env`` under pytest."""
    config = _settings_config(env_prefix=env_prefix)
    if _is_test_runtime():
        config = _settings_config(env_prefix=env_prefix, test=True)

    class Settings(cls):
        model_config = config

    return cast(T, Settings())
