import pytest

from unique_toolkit.monitoring.tracing import TracingSettings


@pytest.fixture(autouse=True, scope="session")
def _isolate_tracing_settings_from_env_file():
    """env_file is resolved at import time, so monkeypatch is too late."""
    original = TracingSettings.model_config.get("env_file")
    TracingSettings.model_config["env_file"] = None
    yield
    TracingSettings.model_config["env_file"] = original
