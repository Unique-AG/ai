"""Webhook entry point: the platform pushes events to this app.

Use this one in production. The app needs a URL the platform can reach, so
locally you need a tunnel such as ngrok. If you cannot expose a port, run
`sse.py` instead.
"""

import logging

from unique_toolkit.app.fast_api_factory import build_unique_custom_app
from unique_toolkit.app.schemas import ChatEvent, EventName
from unique_toolkit.app.unique_settings import UniqueSettings

from mcp_custom_module.handler import handle_event

# Module level so uvicorn can import it. `unique.env` is looked up in the
# working directory, so run this from the example root.
_SETTINGS = UniqueSettings.from_env_auto_with_sdk_init()

app = build_unique_custom_app(
    title="MCP Custom Module Example",
    settings=_SETTINGS,
    event_handler=handle_event,
    event_constructor=ChatEvent,
    subscribed_event_names=[EventName.EXTERNAL_MODULE_CHOSEN],
)


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run("mcp_custom_module.app:app", host="0.0.0.0", port=5001, reload=True)
