import json
import logging
from base64 import b64decode

from google.auth import load_credentials_from_dict
from google.genai._api_client import BaseApiClient
from google.genai.client import AsyncClient

from core.vertexai.settings import VertexAISettings
from core.vertexai.exceptions import (
    VertexAICredentialNotFoundException,
)

_LOGGER = logging.getLogger(__name__)


def _get_vertexai_base_api_client() -> BaseApiClient:
    vertexai_settings = VertexAISettings()
    vertexai_service_account_credentials = vertexai_settings.service_account_credentials
    if vertexai_service_account_credentials is None:
        raise VertexAICredentialNotFoundException()
    service_account_info = json.loads(
        b64decode(vertexai_service_account_credentials).decode("utf-8")
    )

    credentials, project_id = load_credentials_from_dict(
        service_account_info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return BaseApiClient(vertexai=True, credentials=credentials, project=project_id)


def get_vertex_client() -> AsyncClient:
    base_api_client = _get_vertexai_base_api_client()
    return AsyncClient(api_client=base_api_client)
