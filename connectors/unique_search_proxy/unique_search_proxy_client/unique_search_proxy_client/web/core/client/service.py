from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

import httpx
from httpx import AsyncClient

from unique_search_proxy_client.web.settings.client import (
    HttpClientSettings,
    ProxyAuthMode,
    ProxyConfig,
    http_client_settings,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HttpClientPool:
    """Shared httpx client used by engines and crawlers."""

    client: AsyncClient

    async def aclose(self) -> None:
        await self.client.aclose()


def _settings() -> HttpClientSettings:
    return http_client_settings


def _get_proxy_host_and_port(settings: HttpClientSettings) -> tuple[str, int]:
    proxy_host = settings.proxy_host
    proxy_port = settings.proxy_port
    if proxy_host is None or proxy_port is None:
        raise ValueError("Proxy host and port are required")
    return proxy_host, proxy_port


def _build_proxy_url_with_username_password(settings: HttpClientSettings) -> str:
    proxy_host, proxy_port = _get_proxy_host_and_port(settings)
    proxy_username = settings.proxy_username
    proxy_password = settings.proxy_password
    if proxy_username is None or proxy_password is None:
        raise ValueError("Proxy username and password are required")
    return (
        f"{settings.proxy_protocol}://"
        f"{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
    )


def _build_proxy_url_with_tls(settings: HttpClientSettings) -> str:
    proxy_host, proxy_port = _get_proxy_host_and_port(settings)
    return f"{settings.proxy_protocol}://{proxy_host}:{proxy_port}"


def _get_cert_args(settings: HttpClientSettings) -> tuple[str, str] | str:
    proxy_ssl_cert_path = settings.proxy_ssl_cert_path
    if proxy_ssl_cert_path is None:
        raise ValueError("Proxy SSL cert path is required")

    proxy_ssl_key_path = settings.proxy_ssl_key_path
    if proxy_ssl_key_path is None:
        _LOGGER.warning(
            "Proxy SSL key path is not set. Assuming cert path includes key path"
        )
        return proxy_ssl_cert_path
    return proxy_ssl_cert_path, proxy_ssl_key_path


def _get_none_proxy_kwargs(settings: HttpClientSettings) -> ProxyConfig:
    _LOGGER.info("Proxy auth mode: none. Using no proxy")
    return ProxyConfig(
        proxy=None,
        headers=None,
        verify=True,
        trust_env=True,
        cert=None,
    )


def _get_username_password_proxy_kwargs(settings: HttpClientSettings) -> ProxyConfig:
    proxy_url = _build_proxy_url_with_username_password(settings)
    _LOGGER.info(
        "Proxy auth mode: username_password. Using proxy with username and password"
    )
    return ProxyConfig(
        proxy=proxy_url,
        headers=settings.proxy_headers,
        verify=settings.proxy_ssl_ca_bundle_path or True,
    )


def _get_ssl_tls_proxy_kwargs(settings: HttpClientSettings) -> ProxyConfig:
    proxy_url = _build_proxy_url_with_tls(settings)
    cert_args = _get_cert_args(settings)
    _LOGGER.info("Proxy auth mode: ssl_tls. Using proxy with SSL/TLS")
    return ProxyConfig(
        proxy=proxy_url,
        cert=cert_args,
        headers=settings.proxy_headers,
        verify=settings.proxy_ssl_ca_bundle_path or True,
    )


def build_proxy_config(
    settings: HttpClientSettings | None = None,
) -> ProxyConfig:
    client_settings = settings or _settings()
    auth_mode: ProxyAuthMode = client_settings.proxy_auth_mode
    match auth_mode:
        case "none":
            return _get_none_proxy_kwargs(client_settings)
        case "username_password":
            return _get_username_password_proxy_kwargs(client_settings)
        case "ssl_tls":
            return _get_ssl_tls_proxy_kwargs(client_settings)
        case _:
            raise ValueError(f"Invalid proxy auth mode: {auth_mode}")


def build_async_client(
    *,
    settings: HttpClientSettings | None = None,
    timeout: float | None = None,
) -> AsyncClient:
    client_settings = settings or _settings()
    proxy_kwargs = build_proxy_config(client_settings)
    effective_timeout = timeout or client_settings.pool_timeout_seconds
    limits = httpx.Limits(
        max_connections=client_settings.max_connections,
        max_keepalive_connections=client_settings.max_keepalive_connections,
    )
    return AsyncClient(
        proxy=proxy_kwargs.proxy,
        headers=proxy_kwargs.headers,
        verify=proxy_kwargs.verify,
        trust_env=proxy_kwargs.trust_env,
        cert=proxy_kwargs.cert,
        timeout=effective_timeout,
        limits=limits,
    )


def async_client_factory(
    *,
    settings: HttpClientSettings | None = None,
    timeout: float | None = None,
) -> partial[AsyncClient]:
    """Factory for short-lived clients with the shared proxy configuration."""

    client_settings = settings or _settings()
    proxy_kwargs = build_proxy_config(client_settings)
    effective_timeout = timeout or client_settings.pool_timeout_seconds
    return partial(
        AsyncClient,
        proxy=proxy_kwargs.proxy,
        headers=proxy_kwargs.headers,
        verify=proxy_kwargs.verify,
        trust_env=proxy_kwargs.trust_env,
        cert=proxy_kwargs.cert,
        timeout=effective_timeout,
    )


async def create_http_client_pool() -> HttpClientPool:
    client = build_async_client()
    return HttpClientPool(client=client)


def get_http_client_pool(app: FastAPI) -> HttpClientPool:
    pool = getattr(app.state, "http_client_pool", None)
    if pool is None:
        raise RuntimeError("HTTP client pool is not initialized")
    return pool
