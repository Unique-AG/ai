import sys
from pathlib import Path

import pytest

from unique_search_proxy_core.url_safety import UrlSafetySettings


@pytest.mark.ai
def test_url_safety_enabled__defaults_to_true() -> None:
    """
    Purpose: Verify application URL checks remain the default.
    Why this matters: Deployments must be protected without additional configuration.
    Setup summary: Construct default settings and assert checks are enabled.
    """
    settings = UrlSafetySettings()

    assert settings.enabled is True


@pytest.mark.ai
def test_url_safety_enabled__loads_false_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify application checks can be disabled by environment.
    Why this matters: Customer deployments configure this security boundary through Helm.
    Setup summary: Set URL_SAFETY_ENABLED and assert boolean parsing.
    """
    monkeypatch.setenv("URL_SAFETY_ENABLED", "false")

    settings = UrlSafetySettings()

    assert settings.enabled is False


@pytest.mark.ai
def test_url_safety_settings__loads_custom_api_private_hosts_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify application URL-safety settings load from the local dotenv file.
    Why this matters: URL-safety settings are imported before the application loads dotenv.
    Setup summary: Write a production-style .env, load settings, and assert the allowlist.
    """
    from unique_search_proxy_core.url_safety import settings as settings_module

    monkeypatch.chdir(tmp_path)
    monkeypatch.delitem(sys.modules, "pytest")
    (tmp_path / ".env").write_text(
        'CUSTOM_WEB_SEARCH_API_TRUSTED_PRIVATE_HOSTS=["192.168.6.244"]\n',
        encoding="utf-8",
    )

    settings = settings_module._get_settings()

    assert settings.custom_api_trusted_private_hosts == ["192.168.6.244"]
