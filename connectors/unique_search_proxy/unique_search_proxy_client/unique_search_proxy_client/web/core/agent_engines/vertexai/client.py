from __future__ import annotations

import json
import logging
from base64 import b64decode

from google.auth import load_credentials_from_dict
from google.genai._api_client import BaseApiClient
from google.genai.client import AsyncClient

from unique_search_proxy_client.web.settings.providers.vertexai_agent import (
    vertexai_agent_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import read_secret

_LOGGER = logging.getLogger(__name__)


def _get_base_api_client_from_service_account() -> BaseApiClient:
    assert vertexai_agent_credentials.service_account_credentials is not None

    scopes = vertexai_agent_credentials.service_account_scopes or [
        "https://www.googleapis.com/auth/cloud-platform",
    ]
    service_account_info = json.loads(
        b64decode(
            read_secret(vertexai_agent_credentials.service_account_credentials)
        ).decode("utf-8"),
    )
    credentials, project_id = load_credentials_from_dict(
        service_account_info,
        scopes=scopes,
    )
    return BaseApiClient(
        vertexai=True,
        credentials=credentials,
        project=project_id,
    )


def _get_base_api_client_from_adc() -> BaseApiClient:
    return BaseApiClient(vertexai=True)


def get_vertex_client() -> AsyncClient:
    if vertexai_agent_credentials.service_account_credentials is not None:
        _LOGGER.info("Using explicit service account credentials for VertexAI agent")
        base_api_client = _get_base_api_client_from_service_account()
    else:
        _LOGGER.info("Using ADC for VertexAI agent")
        base_api_client = _get_base_api_client_from_adc()
    return AsyncClient(api_client=base_api_client)


def is_vertex_configured() -> bool:
    """Vertex can run with ADC when no explicit service account is set."""
    return True
