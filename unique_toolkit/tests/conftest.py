import logging
import os
from pathlib import Path

import pytest
import unique_sdk
from dotenv import load_dotenv

from tests.test_obj_factory import get_event_obj
from unique_toolkit.chat.service import ChatService

collect_ignore_glob = []
RUN_INTEGRATION_TEST = False 

logger = logging.getLogger(__name__)

def get_env_variable(var_name, default=None):
    """Retrieve an environment variable and log a warning if it is missing."""
    value = os.getenv(var_name, default)
    if value is None:
        logger.warning(f"Environment variable '{var_name}' is not set.")
    return value


# This is only necessary if you run integration tests
if RUN_INTEGRATION_TEST:

    DOTENV_TEST_PATH = Path(__file__).parent/".env.test"
    if not DOTENV_TEST_PATH.exists():
        raise Exception(f"{DOTENV_TEST_PATH.parent} does not exists.")
    load_dotenv(dotenv_path=DOTENV_TEST_PATH)
    
    #Configure the unique_sdk with environment variables
    unique_sdk.api_key = get_env_variable("TEST_API_KEY")
    unique_sdk.app_id = get_env_variable("TEST_APP_ID")
    unique_sdk.api_base = get_env_variable("TEST_API_BASE")

    # Optionally configure logging and HTTP client
    # unique_sdk.log = "debug"
    # unique_sdk.default_http_client = unique_sdk.HTTPXClient()

    # Retrieve additional test identifiers from environment variables
    test_user_id = get_env_variable("TEST_USER_ID")
    test_company_id = get_env_variable("TEST_COMPANY_ID")
    test_chat_id = get_env_variable("TEST_CHAT_ID")
    test_assistant_id = get_env_variable("TEST_ASSISTANT_ID")
    test_user_message_id = get_env_variable("TEST_USER_MESSAGE_ID")
    test_scope_id = get_env_variable("TEST_SCOPE_ID")
else:
    collect_ignore_glob.append("*_integration.py")

@pytest.fixture
def event():
    event = get_event_obj(
        user_id=test_user_id,
        company_id=test_company_id,
        chat_id=test_chat_id,
        assistant_id=test_assistant_id,
        user_message_id=test_user_message_id,
    )
    chat_service = ChatService(event)
    message = chat_service.create_assistant_message("Test assistant message")
    if message.id is not None:
        event.payload.assistant_message.id = message.id
    return event
