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
