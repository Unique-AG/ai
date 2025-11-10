import certifi
from azure.ai.projects import AIProjectClient
from azure.core.credentials import TokenCredential
from azure.core.pipeline.transport._requests_basic import RequestsTransport

from unique_web_search.settings import env_settings


def get_project_client(credentials: TokenCredential, endpoint: str) -> AIProjectClient:
    if env_settings.unique_private_endpoint_transport_enabled:
        transport = RequestsTransport(connection_verify=certifi.where())
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
