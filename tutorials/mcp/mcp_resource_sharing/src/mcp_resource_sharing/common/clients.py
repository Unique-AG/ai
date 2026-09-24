"""OAuth confidential-client registry shared across domains.

The producer IdP only mints tokens for clients it recognises; both the consumer
service and Alice's demo app register here.
"""

from __future__ import annotations

from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings

from mcp_resource_sharing.common.env import settings_config


class ClientSettings(BaseSettings):
    model_config = settings_config(env_prefix="RP_CLIENT_")

    consumer_service_id: str = Field(
        default="resource-consumer-service",
        description="OAuth client id of the consumer MCP server",
    )
    demo_app_id: str = Field(
        default="alice-desktop-app",
        description="OAuth client id of Alice's desktop app (demo/run_demo.py)",
    )

    @cached_property
    def trusted_exchange_clients(self) -> frozenset[str]:
        """Clients the producer IdP will mint producer tokens for."""
        return frozenset({self.consumer_service_id, self.demo_app_id})


client_settings = ClientSettings()
