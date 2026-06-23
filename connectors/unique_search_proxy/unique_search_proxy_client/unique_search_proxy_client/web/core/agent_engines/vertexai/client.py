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
from unique_search_proxy_client.web.settings.secret_str import (
    is_secret_configured,
    read_secret,
)

_LOGGER = logging.getLogger(__name__)


def _get_base_api_client_from_service_account() -> BaseApiClient:
    if not is_secret_configured(vertexai_agent_credentials.service_account_credentials):
        msg = (
            "VERTEXAI_AGENT_CREDENTIAL_TYPE is 'service_account' but "
            "VERTEXAI_AGENT_SERVICE_ACCOUNT_CREDENTIALS is not set."
        )
        raise ValueError(msg)

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
    if vertexai_agent_credentials.credential_type == "service_account":
        _LOGGER.info("Using explicit service account credentials for VertexAI agent")
        base_api_client = _get_base_api_client_from_service_account()
    else:
        _LOGGER.info("Using workload identity (ADC) for VertexAI agent")
        base_api_client = _get_base_api_client_from_adc()
    return AsyncClient(api_client=base_api_client)


def is_vertex_configured() -> bool:
    """Vertex can run with ADC when no explicit service account is set."""
    return True
