import logging
from functools import partial

from httpx import AsyncClient
from pydantic import BaseModel

from unique_web_search.settings import env_settings

logger = logging.getLogger(__name__)


class ProxyConfig(BaseModel):
    verify: bool | str
    proxy: str | None
    headers: dict[str, str] | None
    cert: tuple[str, str] | str | None = None
    trust_env: bool = False


def _get_proxy_host_and_port() -> tuple[str, int]:
    proxy_host = env_settings.proxy_host
    proxy_port = env_settings.proxy_port
    assert proxy_host is not None and proxy_port is not None, (
        "Proxy host and port are required"
    )

    return proxy_host, proxy_port


def _build_proxy_url_with_username_password() -> str:
    proxy_host, proxy_port = _get_proxy_host_and_port()

    proxy_username = env_settings.proxy_username
    proxy_password = env_settings.proxy_password
    assert proxy_username is not None and proxy_password is not None, (
        "Proxy username and password are required"
    )

    return f"{env_settings.proxy_protocol}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"


def _build_proxy_url_with_tls() -> str:
    proxy_host, proxy_port = _get_proxy_host_and_port()
    return f"{env_settings.proxy_protocol}://{proxy_host}:{proxy_port}"


def _get_cert_args() -> tuple[str, str] | str:
    proxy_ssl_cert_path = env_settings.proxy_ssl_cert_path
    assert proxy_ssl_cert_path is not None, "Proxy SSL cert path is required"

    proxy_ssl_key_path = env_settings.proxy_ssl_key_path

    if proxy_ssl_key_path is None:
        logger.warning(
            "Proxy SSL key path is not set. Assuming cert path includes key path"
        )
        return proxy_ssl_cert_path
    else:
        return proxy_ssl_cert_path, proxy_ssl_key_path


def _get_none_proxy_kwargs() -> ProxyConfig:
    logger.info("Proxy auth mode: none. Using no proxy")
    return ProxyConfig(
        proxy=None,
        headers=None,
        verify=True,
        trust_env=True,
        cert=None,
    )


def _get_username_password_proxy_kwargs() -> ProxyConfig:
    proxy_url = _build_proxy_url_with_username_password()
    logger.info(
        "Proxy auth mode: username_password. Using proxy with username and password"
    )
    return ProxyConfig(
        proxy=proxy_url,
        headers=env_settings.proxy_headers,
        verify=env_settings.proxy_ssl_ca_bundle_path or True,
    )


def _get_ssl_tls_proxy_kwargs() -> ProxyConfig:
    proxy_url = _build_proxy_url_with_tls()
    cert_args = _get_cert_args()
    logger.info("Proxy auth mode: ssl_tls. Using proxy with SSL/TLS")
    return ProxyConfig(
        proxy=proxy_url,
        cert=cert_args,
        headers=env_settings.proxy_headers,
        verify=env_settings.proxy_ssl_ca_bundle_path or True,
    )


def _build_client_kwargs() -> ProxyConfig:
    match env_settings.proxy_auth_mode:
        case "none":
            return _get_none_proxy_kwargs()
        case "username_password":
            return _get_username_password_proxy_kwargs()
        case "ssl_tls":
            return _get_ssl_tls_proxy_kwargs()
        case _:
            raise ValueError(f"Invalid proxy auth mode: {env_settings.proxy_auth_mode}")


_client_kwargs = _build_client_kwargs()


async_client = partial(
    AsyncClient,
    proxy=_client_kwargs.proxy,
    headers=_client_kwargs.headers,
    verify=_client_kwargs.verify,
    trust_env=_client_kwargs.trust_env,
    cert=_client_kwargs.cert,
)
