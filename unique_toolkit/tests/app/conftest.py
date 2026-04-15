import pytest

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueChatEventFilterOptions,
)

_SETTINGS_CLASSES = [
    UniqueAuth,
    UniqueApp,
    UniqueApi,
    UniqueChatEventFilterOptions,
    ChatEvent.FilterOptions,
]

_SETTINGS_ENV_VARS = [
    "UNIQUE_APP_ID",
    "UNIQUE_APP_KEY",
    "UNIQUE_APP_BASE_URL",
    "UNIQUE_APP_ENDPOINT",
    "UNIQUE_APP_ENDPOINT_SECRET",
    "UNIQUE_API_BASE_URL",
    "UNIQUE_API_VERSION",
    "UNIQUE_AUTH_COMPANY_ID",
    "UNIQUE_AUTH_USER_ID",
    "APP_ID",
    "API_KEY",
    "KEY",
    "BASE_URL",
    "VERSION",
    "COMPANY_ID",
    "USER_ID",
]


@pytest.fixture(autouse=True, scope="session")
def _isolate_settings_from_env_file():
    """Prevent pydantic-settings from loading the local .env file during tests.

    model_config["env_file"] is resolved at import time, so monkeypatch is too
    late.  This fixture sets it to None for the entire test session and restores
    the original value on teardown.
    """
    originals = {cls: cls.model_config.get("env_file") for cls in _SETTINGS_CLASSES}
    for cls in _SETTINGS_CLASSES:
        cls.model_config["env_file"] = None
    yield
    for cls, original in originals.items():
        cls.model_config["env_file"] = original


@pytest.fixture(autouse=True)
def _isolate_settings_from_shell_env(monkeypatch: pytest.MonkeyPatch):
    """Remove any shell env vars that pydantic-settings would pick up via aliases.

    Without this, a developer's shell (e.g. UNIQUE_APP_KEY="…") silently
    overrides the values set by monkeypatch.setenv inside individual tests.
    """
    for var in _SETTINGS_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
