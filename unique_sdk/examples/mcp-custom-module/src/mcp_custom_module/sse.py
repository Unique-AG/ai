"""Event socket entry point: this script pulls events from the platform.

Development only. The connection opens outbound, so no public URL and no
tunnel are needed — useful on a machine that may not expose a port. In
exchange there is no delivery guarantee, no replay, and the socket closes
after about ten minutes. Production modules use the webhook in `app.py`.

The stream carries every `unique.chat.external-module.chosen` event this app
can see, so the chat event filter is mandatory here: set
`UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS` or
`UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE`, or every event is
dropped.
"""

import logging
import time

from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings

from mcp_custom_module.handler import handle_event

logger = logging.getLogger(__name__)

RECONNECT_SECONDS = 2


def main() -> None:
    settings = UniqueSettings.from_env_auto_with_sdk_init()

    while True:
        logger.info("Opening the event socket")
        for event in get_event_generator(settings, ChatEvent):
            try:
                handle_event(event)
            except Exception:
                # Keep the stream open: a failed message should not end the session.
                logger.exception("Handler failed for chat %s", event.payload.chat_id)

        logger.info("Event socket closed, reconnecting in %ss", RECONNECT_SECONDS)
        time.sleep(RECONNECT_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    main()
