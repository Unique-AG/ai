"""HTTP client module must stay lazy — no egress client at import time."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.ai
def test_http_client_module_does_not_init_registry_on_import() -> None:
    module = importlib.import_module("unique_web_search.services.client.http_client")
    module = importlib.reload(module)

    assert module._registry is None
    assert not hasattr(module, "async_client")


@pytest.mark.ai
def test_http_client_registry__disabled_mode_without_proxy__fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify direct web-search egress rejects disabled checks without a proxy.
    Why this matters: The legacy tool path must not bypass SSRF checks without a proxy.
    Setup summary: Disable checks, return direct proxy settings, and initialize.
    """
    module = importlib.import_module("unique_web_search.services.client.http_client")
    from unique_search_proxy_core.http_client import ProxySettings
    from unique_search_proxy_core.url_safety import (
        UrlSafetyMode,
        UrlSafetySettings,
    )

    monkeypatch.setattr(module, "_registry", None)
    monkeypatch.setattr(
        module,
        "url_safety_settings",
        UrlSafetySettings(mode=UrlSafetyMode.DISABLED_WITH_CORPORATE_PROXY),
    )
    monkeypatch.setattr(module, "proxy_settings_from_env", ProxySettings)

    with pytest.raises(ValueError, match="proxy_host"):
        module.get_http_client_registry()
