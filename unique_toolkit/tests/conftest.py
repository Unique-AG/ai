import os

import pytest
import unique_sdk
from dotenv import load_dotenv

from unique_toolkit.chat.service import ChatService
from unique_toolkit.chat.state import ChatState

load_dotenv(dotenv_path=".env.test")
unique_sdk.api_key = os.getenv("TEST_API_KEY")
unique_sdk.app_id = os.getenv("TEST_APP_ID")
unique_sdk.api_base = os.getenv("TEST_API_BASE")

test_user_id = os.getenv("TEST_USER_ID")
test_company_id = os.getenv("TEST_COMPANY_ID")
test_chat_id = os.getenv("TEST_CHAT_ID")
test_assistant_id = os.getenv("TEST_ASSISTANT_ID")
test_user_message_id = os.getenv("TEST_USER_MESSAGE_ID")
test_scope_id = os.getenv("TEST_SCOPE_ID")

@pytest.fixture
def chat_state():
    chat_state = ChatState(
        user_id=test_user_id, # type: ignore
        company_id=test_company_id, # type: ignore
        assistant_id=test_assistant_id, # type: ignore
        chat_id=test_chat_id, # type: ignore
        user_message_id=test_user_message_id, # type: ignore
        scope_ids=[test_scope_id] # type: ignore
    )
    chat_service = ChatService(chat_state)
    message = chat_service.create_assistant_message("Test assistant message")
    if message.id is not None:
        chat_state.assistant_message_id = message.id
    return chat_state