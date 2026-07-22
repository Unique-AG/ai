from __future__ import annotations

import logging

import certifi
import httpx
from azure.ai.projects.aio import AIProjectClient
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.pipeline.transport import AsyncioRequestsTransport
from azure.identity.aio import DefaultAzureCredential, WorkloadIdentityCredential
from openai import AsyncOpenAI

from unique_search_proxy_client.web.settings.providers.bing_agent import (
    bing_agent_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import NOT_PROVIDED, read_secret

_LOGGER = logging.getLogger(__name__)
_private_endpoint_http_client: httpx.AsyncClient | None = None


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
    resolved_endpoint = endpoint or read_secret(bing_agent_credentials.endpoint)
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


def _get_private_endpoint_http_client() -> httpx.AsyncClient:
    """Return a process-wide certifi-backed httpx client (created once)."""
    global _private_endpoint_http_client
    if _private_endpoint_http_client is None or _private_endpoint_http_client.is_closed:
        _private_endpoint_http_client = httpx.AsyncClient(verify=certifi.where())
    return _private_endpoint_http_client


async def aclose_private_endpoint_http_client() -> None:
    """Close the shared private-endpoint httpx client if it was created."""
    global _private_endpoint_http_client
    if _private_endpoint_http_client is not None and not _private_endpoint_http_client.is_closed:
        await _private_endpoint_http_client.aclose()
    _private_endpoint_http_client = None


def get_openai_client(project_client: AIProjectClient) -> AsyncOpenAI:
    """Return an authenticated AsyncOpenAI client from the Foundry project client.

    When private-endpoint transport is enabled, reuse a shared certifi-backed
    ``httpx.AsyncClient`` so TLS verification matches the AIProjectClient path
    without leaking a new client per request.
    """
    if bing_agent_credentials.use_private_endpoint_transport:
        return project_client.get_openai_client(
            http_client=_get_private_endpoint_http_client(),
        )
    return project_client.get_openai_client()


async def credentials_are_valid(credential: AsyncTokenCredential) -> bool:
    try:
        await credential.get_token(
            bing_agent_credentials.azure_identity_validate_token_url,
        )
        return True
    except Exception as exc:
        _LOGGER.error("Azure identity credentials are invalid: %s", exc)
        return False
