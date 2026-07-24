"""Producer-domain configuration."""

from __future__ import annotations

from pydantic import AnyHttpUrl, Field, computed_field
from pydantic_settings import BaseSettings

from mcp_resource_sharing.common.env import settings_config


class ProducerSettings(BaseSettings):
    model_config = settings_config(env_prefix="RP_PRODUCER_")

    # Discovered at runtime -> must be a reachable URL (metadata + token endpoint).
    idp_issuer: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://keycloak:8080/realms/producer")
    )
    base_url: AnyHttpUrl = Field(default=AnyHttpUrl("http://producer:8001"))
    port: int = Field(default=8001, ge=1, le=65535)
    # Token audience. Per MCP authorization (RFC 8707), tokens are bound to the
    # server's *canonical URI* — override only if your AS uses something else.
    audience: str | None = Field(default=None)
    idp_jwks_uri: AnyHttpUrl = Field(
        default=AnyHttpUrl(
            "http://keycloak:8080/realms/producer/protocol/openid-connect/certs"
        )
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mcp_url(self) -> AnyHttpUrl:
        return AnyHttpUrl(f"{str(self.base_url).rstrip('/')}/mcp")

    @property
    def resource_audience(self) -> str:
        """Audience the producer accepts: its canonical MCP URL (RFC 8707)."""
        return self.audience or str(self.mcp_url)


producer_settings = ProducerSettings()
