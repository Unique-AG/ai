import os

import pytest
import unique_sdk
from dotenv import load_dotenv

from unique_toolkit.chat.service import ChatService
from unique_toolkit.chat.state import ChatState

DOTENV_TEST_PATH = ".env.test"

load_dotenv(dotenv_path=DOTENV_TEST_PATH)
unique_sdk.api_key = os.getenv("TEST_API_KEY") or "test_api_key"
unique_sdk.app_id = os.getenv("TEST_APP_ID") or "test_app_id"
unique_sdk.api_base = os.getenv("TEST_API_BASE") or "http://test.com"

test_user_id = os.getenv("TEST_USER_ID") or "test_user_id"
test_company_id = os.getenv("TEST_COMPANY_ID") or "test_company_id"
test_chat_id = os.getenv("TEST_CHAT_ID") or "test_chat_id"
test_assistant_id = os.getenv("TEST_ASSISTANT_ID") or "test_assistant_id"
test_user_message_id = os.getenv("TEST_USER_MESSAGE_ID") or "test_user_message_id"

# Comment this line to run integration tests, this does currently work only locally
collect_ignore_glob = ["*_integration.py"]


@pytest.fixture
def chat_state():
    chat_state = ChatState(
        user_id=test_user_id,  # type: ignore
        company_id=test_company_id,  # type: ignore
        assistant_id=test_assistant_id,  # type: ignore
        chat_id=test_chat_id,  # type: ignore
        user_message_id=test_user_message_id,  # type: ignore
    )
    chat_service = ChatService(chat_state)
    message = chat_service.create_assistant_message("Test assistant message")
    if message.id is not None:
        chat_state.assistant_message_id = message.id
    return chat_state
