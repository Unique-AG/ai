import logging

import certifi
import httpx
from azure.ai.projects.aio import AIProjectClient
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.pipeline.transport import AsyncioRequestsTransport
from azure.identity.aio import DefaultAzureCredential, WorkloadIdentityCredential
from openai import AsyncOpenAI

from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)
_private_endpoint_http_client: httpx.AsyncClient | None = None


def _get_workload_identity_credentials(
    with_request_transport: bool = False,
) -> WorkloadIdentityCredential:
    if with_request_transport:
        transport = AsyncioRequestsTransport(connection_verify=certifi.where())
        return WorkloadIdentityCredential(transport=transport)
    return WorkloadIdentityCredential()


def get_credentials() -> AsyncTokenCredential:
    match env_settings.azure_identity_credential_type:
        case "workload":
            return _get_workload_identity_credentials(
                env_settings.use_unique_private_endpoint_transport
            )
        case "default":
            return DefaultAzureCredential()
        case other:
            raise ValueError(f"Invalid Azure identity credential type: {other}")


async def credentials_are_valid(credentials: AsyncTokenCredential) -> bool:
    _LOGGER.info("Validating Azure identity credentials")
    try:
        await credentials.get_token(
            env_settings.azure_identity_credentials_validate_token_url
        )
        _LOGGER.info("Azure identity credentials are valid")
        return True
    except Exception as e:
        _LOGGER.error(f"Azure identity credentials are invalid: {e}")
        return False


def get_project_client(
    credentials: AsyncTokenCredential, endpoint: str
) -> AIProjectClient:
    endpoint = env_settings.azure_ai_project_endpoint or endpoint

    if not endpoint:
        raise ValueError(
            "Azure AI project endpoint is not set from environment variables or configuration"
        )

    if env_settings.use_unique_private_endpoint_transport:
        transport = AsyncioRequestsTransport(connection_verify=certifi.where())
        return AIProjectClient(
            credential=credentials,
            endpoint=endpoint,
            transport=transport,
        )
    else:
        return AIProjectClient(
            credential=credentials,
            endpoint=endpoint,
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
    if (
        _private_endpoint_http_client is not None
        and not _private_endpoint_http_client.is_closed
    ):
        await _private_endpoint_http_client.aclose()
    _private_endpoint_http_client = None


def get_openai_client(project_client: AIProjectClient) -> AsyncOpenAI:
    """Return an authenticated AsyncOpenAI client from the Foundry project client.

    When private-endpoint transport is enabled, reuse a shared certifi-backed
    ``httpx.AsyncClient`` so TLS verification matches the AIProjectClient path
    without leaking a new client per request.
    """
    if env_settings.use_unique_private_endpoint_transport:
        return project_client.get_openai_client(
            http_client=_get_private_endpoint_http_client(),
        )
    return project_client.get_openai_client()
