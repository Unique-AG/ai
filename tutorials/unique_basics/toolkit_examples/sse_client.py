import json
import logging
import os

from dotenv import load_dotenv
from sseclient import SSEClient

import unique_sdk

# For more details about Event Socket and how to use it, please refer to the following link:
# https://unique-ch.atlassian.net/wiki/spaces/PUB/pages/631406621/Event+Socket+Streaming+Endpoint+SSE+-+Webhooks+Drop-In

# Module and subscription constants
MODULE_NAME = "AssistantDemo"
SUBSCRIPTIONS = "unique.chat.user-message.created"

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv("../.env.app_next_prod", override=True)


def get_env_val(var_name: str) -> str:
    val = os.environ.get(var_name)
    if not val:
        raise ValueError(f"Env variable {var_name} not set.")
    return val


# Set SDK configuration
unique_sdk.api_key = get_env_val("API_KEY")
unique_sdk.app_id = get_env_val("APP_ID")


def get_sse_client() -> SSEClient:
    url = f'{get_env_val("BASE_URL")}/public/event-socket/events/stream?subscriptions={SUBSCRIPTIONS}'
    headers = {
        "Authorization": f'Bearer {get_env_val("API_KEY")}',
        "x-app-id": get_env_val("APP_ID"),
        "x-company-id": get_env_val("COMPANY_ID"),
        "x-user-id": "",
    }

    print(url)
    print(headers)
    return SSEClient(url=url, headers=headers)


def process_event(event_data) -> None:
    try:
        event = json.loads(event_data)
        logger.debug(f"Event details: {event}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e}")
        return

    if (
        event
        and event["event"] in SUBSCRIPTIONS.split(",")
        and event["payload"]["assistantId"] == get_env_val("ASSISTANT_ID")
    ):
        logger.info(f"Event subscription received: {SUBSCRIPTIONS}")

        # Send a message back to the user
        try:
            unique_sdk.Message.create(
                user_id=event["userId"],
                company_id=event["companyId"],
                chatId=event["payload"]["chatId"],
                assistantId=get_env_val("ASSISTANT_ID"),
                text="Hello from the Assistant Demo! 🚀",
                role="ASSISTANT",
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")


def event_socket():
    for event in get_sse_client():
        logger.debug("New event received.")
        if not event.data:
            logger.warning("Received an empty message.")
            continue
        else:
            process_event(event.data)


if __name__ == "__main__":
    event_socket()
