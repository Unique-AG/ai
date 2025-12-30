import json
import logging
from base64 import b64decode

from google.auth import load_credentials_from_dict
from google.genai._api_client import BaseApiClient
from google.genai.client import AsyncClient

from unique_web_search.services.search_engine.utils.vertexai.exceptions import (
    VertexAICredentialNotFoundException,
)
from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)


def _get_vertexai_base_api_client() -> BaseApiClient:
    if env_settings.vertexai_service_account_credentials is None:
        raise VertexAICredentialNotFoundException()

    scopes = env_settings.vertexai_service_account_scopes or [
        "https://www.googleapis.com/auth/cloud-platform"
    ]

    service_account_info = json.loads(
        b64decode(env_settings.vertexai_service_account_credentials).decode("utf-8")
    )
    credentials, project_id = load_credentials_from_dict(
        service_account_info, scopes=scopes
    )
    return BaseApiClient(vertexai=True, credentials=credentials, project=project_id)


def get_vertex_client() -> AsyncClient | None:
    try:
        base_api_client = _get_vertexai_base_api_client()
        return AsyncClient(api_client=base_api_client)
    except Exception as e:
        _LOGGER.error(f"Error getting VertexAI client: {e}")
        return None
