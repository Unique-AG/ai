import logging
import os

from google.genai._api_client import BaseApiClient
from google.genai.client import AsyncClient

from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)


def get_vertex_client() -> AsyncClient | None:
    try:
        service_account_file = env_settings.vertexai_service_account_file
        if service_account_file is None:
            _LOGGER.error("VertexAI service account file is not set")
            return None
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_file
        return AsyncClient(api_client=BaseApiClient(vertexai=True))
    except Exception as e:
        _LOGGER.error(f"Error getting VertexAI client: {e}")
        return None
