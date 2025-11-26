import logging
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_LOGGER = logging.getLogger(__name__)

ProxyAuthMode = Literal["none", "username_password", "ssl_tls"]
ProxyProtocol = Literal["http", "https"]

WebSearchMode = Literal["v1", "v2"]
AZURE_IDENTITY_CREDENTIAL_TYPE = Literal["workload", "default"]


class Base(BaseSettings):
    env: str | None = None
    log_level: str | None = None
    tiktoken_cache_dir: str = "./tiktoken_cache/"

    web_search_mode: WebSearchMode | None = None

    # Active search engines
    active_search_engines: list[str] = ["google"]

    # Default Crawlers
    active_inhouse_crawlers: list[str] = ["basic", "crawl4ai"]

    # Google Search settings
    google_search_api_key: str | None = None
    google_search_api_endpoint: str | None = None
    google_search_engine_id: str | None = None

    # Jina API settings
    jina_api_key: str | None = None
    jina_search_api_endpoint: str = "https://s.jina.ai/"
    jina_reader_api_endpoint: str = "https://r.jina.ai/"

    # Firecrawl API settings
    firecrawl_api_key: str | None = None

    # Tavily API settings
    tavily_api_key: str | None = None

    # Brave Search API settings
    brave_search_api_key: str | None = None
    brave_search_api_endpoint: str | None = None

    # VertexAI API settings
    vertexai_service_account_credentials: str | None = None
    vertexai_service_account_scopes: list[str] | None = None

    # Proxy settings
    ## Shared settings
    proxy_auth_mode: ProxyAuthMode = "none"
    proxy_protocol: ProxyProtocol = "http"
    proxy_host: str | None = None
    proxy_port: int | None = None
    proxy_headers: dict[str, str] = {}

    ## If specific SSL/TLS certificate is required other than the default
    proxy_ssl_ca_bundle_path: str | None = None

    ##  For username/password authentication
    proxy_username: str | None = None
    proxy_password: str | None = None

    ## For SSL/TLS authentication
    proxy_ssl_cert_path: str | None = None
    proxy_ssl_key_path: str | None = None

    ## For Azure Identity Credential
    unique_private_endpoint_transport_enabled: bool | None = False
    default_azure_identity_credential_type: AZURE_IDENTITY_CREDENTIAL_TYPE | None = (
        "default"
    )
    default_azure_identity_credentials_validate_token_url: str | None = (
        "https://management.azure.com/.default"
    )

    @property
    def active_crawlers(self) -> list[str]:
        "Dynamically determine the active crawlers based on the API keys provided"
        default_crawlers = self.active_inhouse_crawlers
        if self.firecrawl_api_key:
            default_crawlers.append("firecrawl")
        if self.jina_api_key:
            default_crawlers.append("jina")
        if self.tavily_api_key:
            default_crawlers.append("tavily")

        return default_crawlers

    @property
    def default_web_search_mode(self) -> WebSearchMode:
        if self.web_search_mode is None:
            _LOGGER.warning("No default web search mode set, using v1")
            return "v1"
        return self.web_search_mode

    @property
    def azure_identity_credential_type(self) -> AZURE_IDENTITY_CREDENTIAL_TYPE:
        if self.default_azure_identity_credential_type is None:
            _LOGGER.warning(
                "No default Azure identity credential type set, using default"
            )
            return "default"
        return self.default_azure_identity_credential_type

    @property
    def azure_identity_credentials_validate_token_url(self) -> str:
        if self.default_azure_identity_credentials_validate_token_url is None:
            _LOGGER.warning(
                "No default Azure identity credentials validate token url set, using default"
            )
            return "https://management.azure.com/.default"
        return self.default_azure_identity_credentials_validate_token_url

    @property
    def use_unique_private_endpoint_transport(self) -> bool:
        if self.unique_private_endpoint_transport_enabled is None:
            _LOGGER.warning(
                "No default unique private endpoint transport enabled set, using False"
            )
            return False
        return self.unique_private_endpoint_transport_enabled


class Settings(Base):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / ".env", extra="ignore"
    )


class TestSettings(Base):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / "tests/test.env", extra="ignore"
    )


def get_settings() -> Base:
    """
    Dynamically load settings, switching to test environment if running under pytest.

    :return: Settings instance.
    """
    if "pytest" in sys.modules:
        # Dynamically adjust to use `test.env` if running under pytest
        return TestSettings()
    return Settings()


env_settings: Base = get_settings()
