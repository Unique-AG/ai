from unittest.mock import patch

import pytest

from unique_web_search.services.proxy.bridge import open_search_proxy_client

pytestmark = pytest.mark.ai


@pytest.mark.asyncio
async def test_open_search_proxy_client__sends_service_id_header():
    with patch(
        "unique_web_search.services.proxy.bridge.env_settings.search_proxy_base_url",
        "http://proxy",
    ):
        async with open_search_proxy_client(timeout=1) as client:
            headers = client.openapi.get_async_httpx_client().headers

    assert headers["x-service-id"] == "assistants-core"
