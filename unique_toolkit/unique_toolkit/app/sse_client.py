from unique_toolkit.app.unique_settings import UniqueSettings
from sseclient import SSEClient
from logging import getLogger



LOGGER = getLogger(__name__)

def get_sse_client(
    unique_settings: UniqueSettings, subscriptions: list[str]
) -> SSEClient:
    url = f"{unique_settings.app.base_url}/public/event-socket/events/stream?subscriptions={','.join(subscriptions)}"
    headers = {
        "Authorization": f"Bearer {unique_settings.app.key}",
        "x-app-id": unique_settings.app.id,
        "x-company-id": unique_settings.auth.company_id,
    }
    LOGGER.info(f"SSEheaders: {headers}")
    LOGGER.info(f"SSE Url: {url}")
    return SSEClient(url=url, headers=headers)

