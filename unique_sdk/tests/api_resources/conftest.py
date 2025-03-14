import os

# from pathlib import Path
from types import SimpleNamespace

import pytest

import unique_sdk

unique_sdk.api_base = os.getenv("TEST_BASE_URL", "http://localhost:8092/public")
unique_sdk.api_key = os.getenv("TEST_API_KEY", "dummy")
unique_sdk.app_id = os.getenv("TEST_APP_ID", "dummy")


# Retrieve additional test identifiers from environment variables
test_user_id = os.getenv("TEST_USER_ID", "307820057868697608")
test_company_id = os.getenv("TEST_COMPANY_ID", "307820057868632072")
test_chat_id = os.getenv("TEST_CHAT_ID", "chat_mkj2l5c7p2e3wq1s9085xa4a")
test_user_message_id = os.getenv("TEST_USER_MESSAGE_ID", "msg_gaqsqjxbwxt12gc6aj5he77v")
test_assistant_messasge_id = os.getenv(
    "TEST_ASSISTANT_MESSAGE_ID", "msg_gtys6vxtku893fum1wguemsh"
)
test_assistant_id = os.getenv("TEST_ASSISTANT_ID", "assistant_c52lo0m25rxurhegrq5ifm4k")


@pytest.fixture(autouse=True)
def event():
    mock_obj = SimpleNamespace(
        user_id=test_user_id,
        company_id=test_company_id,
        chat_id=test_chat_id,
        user_message_id=test_user_message_id,
        assistant_message_id=test_assistant_messasge_id,
        assistant_id=test_assistant_id,
    )
    return mock_obj
