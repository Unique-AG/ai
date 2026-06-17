from __future__ import annotations

import socket

import pytest

import unique_search_proxy_core.url_safety.dns as url_safety_dns


@pytest.fixture
def fake_public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a deterministic public IP for dotted hostnames in URL safety tests."""

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


@pytest.fixture
def disable_url_safety_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Policy/resolver tests validate URLs directly, without HTTP redirect discovery."""
    import unique_search_proxy_core.url_safety.service as service_module

    monkeypatch.setattr(
        service_module,
        "url_safety_settings",
        service_module.url_safety_settings.model_copy(
            update={"resolve_redirects": False}
        ),
    )
