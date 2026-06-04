import os
import sys
from pathlib import Path

from pydantic_settings import SettingsConfigDict


def get_env_path() -> Path:
    return Path(os.getcwd()) / ".env"


def settings_config(
    *,
    env_prefix: str = "",
    test: bool = False,
) -> SettingsConfigDict:
    env_file = Path(os.getcwd()) / ("tests/test.env" if test else ".env")
    return SettingsConfigDict(
        extra="ignore",
        env_prefix=env_prefix,
        case_sensitive=False,
        env_file=env_file,
        env_file_encoding="utf-8",
        frozen=True,
    )


def is_test_runtime() -> bool:
    return "pytest" in sys.modules
