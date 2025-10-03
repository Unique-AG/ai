import logging
import os
from pathlib import Path
from typing import Any, Dict

import pytest
import unique_sdk
from dotenv import load_dotenv
from pydantic import SecretStr

from tests.test_obj_factory import get_event_obj
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueChatEventFilterOptions,
    UniqueSettings,
)
from unique_toolkit.chat.service import ChatService

collect_ignore_glob = []
RUN_INTEGRATION_TEST = False

logger = logging.getLogger(__name__)


def get_env_variable(var_name, default=None):
    """Retrieve an environment variable and log a warning if it is missing."""
    value = os.getenv(var_name, default)
    if value is None:
        logger.warning(f"Environment variable '{var_name}' is not set.")
        value = var_name
    return value


# This is only necessary if you run integration tests
if RUN_INTEGRATION_TEST:
    DOTENV_TEST_PATH = Path(__file__).parent / ".env.test"
    if not DOTENV_TEST_PATH.exists():
        raise Exception(f"{DOTENV_TEST_PATH.parent} does not exists.")
    load_dotenv(dotenv_path=DOTENV_TEST_PATH)
else:
    collect_ignore_glob.append("*_integration.py")

# Configure the unique_sdk with environment variables
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


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def base_chat_event_data() -> ChatEvent:
    """Base chat event that can be modified for specific tests."""
    event_data: Dict[str, Any] = {
        "id": "test-event",
        "event": "unique.chat.external-module.chosen",
        "userId": "test-user",
        "companyId": "test-company",
        "payload": {
            "name": "test_module",
            "description": "Test description",
            "configuration": {},
            "chatId": "test-chat",
            "assistantId": "test-assistant",
            "userMessage": {
                "id": "msg1",
                "text": "Hello",
                "createdAt": "2023-01-01T00:00:00Z",
                "originalText": "Hello",
                "language": "en",
            },
            "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
        },
        "createdAt": 1672531200,
        "version": "1.0",
    }
    return ChatEvent.model_validate(event_data)


@pytest.fixture
def base_unique_settings() -> UniqueSettings:
    """Base UniqueSettings that can be modified for specific tests.

    This fixture properly handles BaseSettings field resolution by:
    1. Creating objects with defaults first
    2. Overriding values after construction to bypass field resolution
    3. Ensuring consistent test values regardless of environment
    """
    # Create auth settings (these work fine with constructor values)
    auth = UniqueAuth(
        company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
    )

    # Create app settings - must override after construction due to BaseSettings
    app = UniqueApp()
    app.id = SecretStr("test-id")
    app.key = SecretStr("test-key")
    app.base_url = "https://api.example.com"
    app.endpoint = "/v1/endpoint"
    app.endpoint_secret = SecretStr("test-endpoint-secret")

    # Create API settings (these work fine with constructor values)
    api = UniqueApi(
        base_url="https://api.example.com",
        version="2023-12-06",
    )

    return UniqueSettings(auth=auth, app=app, api=api)


@pytest.fixture
def unique_settings_with_filters(
    base_unique_settings: UniqueSettings,
) -> UniqueSettings:
    """UniqueSettings with filter options for testing filtering functionality."""
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["assistant1", "assistant2"],
        references_in_code=["module1", "module2"],
    )
    return UniqueSettings(
        auth=base_unique_settings.auth,
        app=base_unique_settings.app,
        api=base_unique_settings.api,
        chat_event_filter_options=filter_options,
    )


@pytest.fixture
def unique_settings_with_assistant_filter(
    base_unique_settings: UniqueSettings,
) -> UniqueSettings:
    """UniqueSettings with only assistant_id filtering."""
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["assistant1"],
        references_in_code=[],
    )
    return UniqueSettings(
        auth=base_unique_settings.auth,
        app=base_unique_settings.app,
        api=base_unique_settings.api,
        chat_event_filter_options=filter_options,
    )


@pytest.fixture
def unique_settings_with_empty_filters(
    base_unique_settings: UniqueSettings,
) -> UniqueSettings:
    """UniqueSettings with empty filter lists."""
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=[],
        references_in_code=[],
    )
    return UniqueSettings(
        auth=base_unique_settings.auth,
        app=base_unique_settings.app,
        api=base_unique_settings.api,
        chat_event_filter_options=filter_options,
    )
