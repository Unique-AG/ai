from __future__ import annotations

import logging

import certifi
from azure.ai.projects.aio import AIProjectClient
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.pipeline.transport import AsyncioRequestsTransport
from azure.identity.aio import DefaultAzureCredential, WorkloadIdentityCredential

from unique_search_proxy_client.web.settings.providers.bing_agent import (
    bing_agent_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import NOT_PROVIDED

_LOGGER = logging.getLogger(__name__)


def get_credentials() -> AsyncTokenCredential:
    match bing_agent_credentials.azure_identity_credential_type:
        case "workload":
            if bing_agent_credentials.use_private_endpoint_transport:
                transport = AsyncioRequestsTransport(connection_verify=certifi.where())
                return WorkloadIdentityCredential(transport=transport)
            return WorkloadIdentityCredential()
        case "default":
            return DefaultAzureCredential()
        case other:
            msg = f"Invalid Azure identity credential type: {other}"
            raise ValueError(msg)


def get_project_client(
    credential: AsyncTokenCredential,
    *,
    endpoint: str | None = None,
) -> AIProjectClient:
    resolved_endpoint = endpoint or bing_agent_credentials.endpoint
    if not resolved_endpoint or resolved_endpoint == NOT_PROVIDED:
        msg = "Bing agent Azure AI project endpoint is not configured"
        raise ValueError(msg)

    if bing_agent_credentials.use_private_endpoint_transport:
        transport = AsyncioRequestsTransport(connection_verify=certifi.where())
        return AIProjectClient(
            credential=credential,
            endpoint=resolved_endpoint,
            transport=transport,
        )
    return AIProjectClient(
        credential=credential,
        endpoint=resolved_endpoint,
    )


async def credentials_are_valid(credential: AsyncTokenCredential) -> bool:
    try:
        await credential.get_token(
            bing_agent_credentials.azure_identity_validate_token_url,
        )
        return True
    except Exception as exc:
        _LOGGER.error("Azure identity credentials are invalid: %s", exc)
        return False
