"""Consumer-domain configuration."""

from __future__ import annotations

from functools import cached_property
from typing import Annotated

from pydantic import AnyHttpUrl, BeforeValidator, Field, computed_field
from pydantic_settings import BaseSettings, NoDecode

from mcp_resource_sharing.common.env import settings_config


def _parse_http_url_csv(value: object) -> list[str]:
    """Accept a comma-separated string or a list (from defaults / env)."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    raise TypeError(f"expected str or list, got {type(value).__name__}")


HttpUrlList = Annotated[
    list[AnyHttpUrl],
    NoDecode,
    BeforeValidator(_parse_http_url_csv),
]


class ConsumerSettings(BaseSettings):
    model_config = settings_config(env_prefix="RP_CONSUMER_")

    idp_issuer: AnyHttpUrl = Field(default=AnyHttpUrl("http://dex:5556"))
    base_url: AnyHttpUrl = Field(default=AnyHttpUrl("http://consumer:8002"))
    port: int = Field(default=8002, ge=1, le=65535)
    # Dex issues tokens with aud=<client_id>, not the canonical MCP URL.
    audience: str | None = Field(default="alice-desktop-app")
    idp_jwks_uri: AnyHttpUrl = Field(default=AnyHttpUrl("http://dex:5556/keys"))

    # Trust boundary: producers this consumer is willing to talk to at all.
    allowed_producers: HttpUrlList = Field(
        default=[AnyHttpUrl("http://producer:8001/mcp")]
    )

    @property
    def idp_issuer_value(self) -> str:
        """Issuer string for JWT verification (no trailing slash)."""
        return str(self.idp_issuer).rstrip("/")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mcp_url(self) -> AnyHttpUrl:
        return AnyHttpUrl(f"{str(self.base_url).rstrip('/')}/mcp")

    @property
    def resource_audience(self) -> str:
        """Audience the consumer accepts: its canonical MCP URL (RFC 8707)."""
        return self.audience or str(self.mcp_url)

    @cached_property
    def allowed_producer_urls(self) -> frozenset[str]:
        return frozenset(str(url) for url in self.allowed_producers)

    def is_producer_allowed(self, producer_url: str) -> bool:
        return producer_url in self.allowed_producer_urls


consumer_settings = ConsumerSettings()
