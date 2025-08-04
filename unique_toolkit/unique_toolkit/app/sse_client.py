from logging import getLogger

from sseclient import SSEClient

from unique_toolkit.app.unique_settings import UniqueSettings

LOGGER = getLogger(__name__)


def get_sse_client(
    unique_settings: UniqueSettings,
    subscriptions: list[str],
) -> SSEClient:
    url = f"{unique_settings.app.base_url}/public/event-socket/events/stream?subscriptions={','.join(subscriptions)}"
    headers = {
        "Authorization": f"Bearer {unique_settings.app.key.get_secret_value()}",
        "x-app-id": unique_settings.app.id.get_secret_value(),
        "x-company-id": unique_settings.auth.company_id.get_secret_value(),
    }
    return SSEClient(url=url, headers=headers)
