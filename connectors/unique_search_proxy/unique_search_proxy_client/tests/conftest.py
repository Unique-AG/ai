# Shared pytest fixtures for unique_search_proxy tests.

from __future__ import annotations

import socket

import pytest
import unique_search_proxy_core.url_safety.dns as url_safety_dns


@pytest.fixture(autouse=True)
def disable_context_header_enforcement_for_legacy_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep existing TestClient integration tests working without tenant headers."""
    from unique_search_proxy_client.web.settings.app import AppSettings

    monkeypatch.setattr(
        "unique_search_proxy_client.web.middleware.context.app_settings",
        AppSettings(require_context_headers=False),
    )


@pytest.fixture(autouse=True)
def stable_public_dns_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a deterministic public IP for dotted hostnames during unit tests."""

    def fake_getaddrinfo(host: str, *args: object, **kwargs: object) -> list[tuple]:
        normalized_host = str(host).rstrip(".").lower()
        if "." not in normalized_host:
            raise socket.gaierror("single-label host not resolved in tests")

        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", 443),
            )
        ]

    monkeypatch.setattr(url_safety_dns.socket, "getaddrinfo", fake_getaddrinfo)


@pytest.fixture(autouse=True)
def disable_url_safety_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate crawl URLs directly in tests without HTTP redirect discovery."""
    import unique_search_proxy_core.url_safety.service as service_module

    monkeypatch.setattr(
        service_module,
        "url_safety_settings",
        service_module.url_safety_settings.model_copy(
            update={"resolve_redirects": False}
        ),
    )
