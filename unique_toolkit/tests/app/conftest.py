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
