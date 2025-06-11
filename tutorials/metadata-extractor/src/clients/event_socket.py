import backoff
import httpx
from quart import current_app as app
from src.settings import get_settings
from sseclient import SSEClient


class EventSocketClient:
    def __init__(self, max_retries=5, retry_delay=5):
        self.settings = get_settings()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None

    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPError, ConnectionError),
        max_tries=5,
    )
    def event_socket(self):
        """Establishes event socket connection with retry logic."""
        app.logger.info("Establishing event socket connection...")
        url = self._build_url()
        headers = self._build_headers()

        try:
            self.connection = SSEClient(url=url, headers=headers)
            return self.connection
        except Exception as e:
            app.logger.error(f"Failed to establish event socket connection: {str(e)}")
            raise

    def _build_url(self):
        if not self.settings.subscriptions:
            raise ValueError("Subscriptions are not set")
        subscriptions_string = ",".join(self.settings.subscriptions)
        return f"{self.settings.base_url}/public/event-socket/events/stream?subscriptions={subscriptions_string}"

    def _build_headers(self):
        return {
            "Authorization": f"Bearer {self.settings.api_key}",
            "x-app-id": self.settings.app_id,
            "x-company-id": self.settings.company_id,
        }
