import os

import pytest
import unique_sdk
from dotenv import load_dotenv

from tests.test_obj_factory import get_event_obj
from unique_toolkit.chat.service import ChatService

DOTENV_TEST_PATH = ".env.test"

load_dotenv(dotenv_path=DOTENV_TEST_PATH)
unique_sdk.api_key = os.getenv("TEST_API_KEY") or "test_api_key"
unique_sdk.app_id = os.getenv("TEST_APP_ID") or "test_app_id"
unique_sdk.api_base = os.getenv("TEST_API_BASE") or "http://test.com"
# unique_sdk.log = "debug"
# unique_sdk.default_http_client = unique_sdk.HTTPXClient()

test_user_id = os.getenv("TEST_USER_ID") or "test_user_id"
test_company_id = os.getenv("TEST_COMPANY_ID") or "test_company_id"
test_chat_id = os.getenv("TEST_CHAT_ID") or "test_chat_id"
test_assistant_id = os.getenv("TEST_ASSISTANT_ID") or "test_assistant_id"
test_user_message_id = os.getenv("TEST_USER_MESSAGE_ID") or "test_user_message_id"
test_scope_id = os.getenv("TEST_SCOPE_ID") or "test_scope_id"

# Comment this line to run integration tests, this does currently work only locally
collect_ignore_glob = ["*_integration.py"]


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
