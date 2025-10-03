import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import pytest
import unique_sdk
from dotenv import load_dotenv
from pydantic import SecretStr

from tests.test_obj_factory import get_event_obj
from unique_toolkit.agentic.evaluation.config import EvaluationMetricConfig
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationAssessmentMessage,
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.app.schemas import (
    ChatEvent,
    Event,
    EventAssistantMessage,
    EventName,
    EventPayload,
    EventUserMessage,
)
from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueChatEventFilterOptions,
    UniqueSettings,
)
from unique_toolkit.chat.schemas import (
    ChatMessage,
    ChatMessageAssessment,
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
    ChatMessageRole,
    MessageExecution,
    MessageExecutionType,
    MessageExecutionUpdateStatus,
    MessageLog,
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

# ============================================================================
# UniqueSettings Test Fixtures
# ============================================================================

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


# ============================================================================
# Base Component Fixtures
# ============================================================================


@pytest.fixture
def base_auth() -> UniqueAuth:
    """Base UniqueAuth fixture that can be modified for specific tests."""
    return UniqueAuth(
        company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
    )


@pytest.fixture
def base_app() -> UniqueApp:
    """Base UniqueApp fixture that can be modified for specific tests."""
    app = UniqueApp()
    app.id = SecretStr("test-id")
    app.key = SecretStr("test-key")
    app.base_url = "https://api.example.com"
    app.endpoint = "/v1/endpoint"
    app.endpoint_secret = SecretStr("test-endpoint-secret")
    return app


@pytest.fixture
def base_api() -> UniqueApi:
    """Base UniqueApi fixture that can be modified for specific tests."""
    return UniqueApi(
        base_url="https://api.example.com",
        version="2023-12-06",
    )


@pytest.fixture
def base_chat_event_filter_options() -> UniqueChatEventFilterOptions:
    """Base UniqueChatEventFilterOptions fixture with empty lists."""
    return UniqueChatEventFilterOptions(
        assistant_ids=[],
        references_in_code=[],
    )


# ============================================================================
# Complete Settings Fixtures
# ============================================================================


@pytest.fixture
def base_unique_settings(
    base_auth: UniqueAuth,
    base_app: UniqueApp,
    base_api: UniqueApi,
) -> UniqueSettings:
    """Base UniqueSettings fixture that can be modified for specific tests."""
    return UniqueSettings(
        auth=base_auth,
        app=base_app,
        api=base_api,
    )


@pytest.fixture
def unique_settings_with_filters(
    base_auth: UniqueAuth,
    base_app: UniqueApp,
    base_api: UniqueApi,
) -> UniqueSettings:
    """UniqueSettings with populated filter options."""
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["assistant1", "assistant2"],
        references_in_code=["module1", "module2"],
    )
    return UniqueSettings(
        auth=base_auth,
        app=base_app,
        api=base_api,
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


# ============================================================================
# Environment Variable Fixtures
# ============================================================================


@pytest.fixture
def prefixed_env_vars() -> Dict[str, str]:
    """Environment variables with UNIQUE_ prefix."""
    return {
        "UNIQUE_AUTH_COMPANY_ID": "prefixed-company",
        "UNIQUE_AUTH_USER_ID": "prefixed-user",
        "UNIQUE_APP_ID": "prefixed-id",
        "UNIQUE_APP_KEY": "prefixed-key",
        "UNIQUE_APP_BASE_URL": "https://prefixed.api.example.com",
        "UNIQUE_APP_ENDPOINT": "/v1/prefixed-endpoint",
        "UNIQUE_APP_ENDPOINT_SECRET": "prefixed-endpoint-secret",
        "UNIQUE_API_BASE_URL": "https://prefixed.api.example.com",
        "UNIQUE_API_VERSION": "2024-02-01",
    }


@pytest.fixture
def legacy_env_vars() -> Dict[str, str]:
    """Legacy environment variables without prefix."""
    return {
        "BASE_URL": "https://legacy.api.example.com",
        "VERSION": "2024-01-01",
        "COMPANY_ID": "legacy-company",
        "USER_ID": "legacy-user",
        "APP_ID": "legacy-app-id",
        "API_KEY": "legacy-app-key",
    }


@pytest.fixture
def mixed_env_vars() -> Dict[str, str]:
    """Mixed environment variables with both prefixed and legacy names."""
    return {
        "UNIQUE_API_BASE_URL": "https://prefixed.api.example.com",
        "VERSION": "2024-01-01",
        "UNIQUE_AUTH_COMPANY_ID": "prefixed-company",
        "USER_ID": "legacy-user",
        "APP_ID": "legacy-app-id",
        "UNIQUE_APP_KEY": "prefixed-app-key",
    }


@pytest.fixture
def filter_options_env_vars() -> Dict[str, str]:
    """Environment variables for chat event filter options."""
    return {
        "UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS": '["assistant1", "assistant2"]',
        "UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE": '["module1", "module2"]',
    }


# ============================================================================
# Environment File Fixtures
# ============================================================================


@pytest.fixture
def env_file_content_prefixed() -> str:
    """Content for .env file with prefixed variables."""
    return """
UNIQUE_AUTH_COMPANY_ID=file-company
UNIQUE_AUTH_USER_ID=file-user
UNIQUE_APP_ID=file-id
UNIQUE_APP_KEY=file-key
UNIQUE_APP_BASE_URL=https://api.file-example.com
UNIQUE_APP_ENDPOINT=/v1/file-endpoint
UNIQUE_APP_ENDPOINT_SECRET=file-endpoint-secret
UNIQUE_API_BASE_URL=https://api.file-example.com
UNIQUE_API_VERSION=2023-12-06
"""


@pytest.fixture
def env_file_content_legacy() -> str:
    """Content for .env file with legacy variables."""
    return """
BASE_URL=https://legacy-file.api.example.com
VERSION=2024-03-01
COMPANY_ID=legacy-file-company
USER_ID=legacy-file-user
APP_ID=legacy-file-app-id
API_KEY=legacy-file-api-key
"""


@pytest.fixture
def env_file_content_mixed() -> str:
    """Content for .env file with mixed prefixed and legacy variables."""
    return """
UNIQUE_API_BASE_URL=https://prefixed-file.api.example.com
VERSION=2024-legacy-version
UNIQUE_AUTH_COMPANY_ID=prefixed-file-company
USER_ID=legacy-file-user
APP_ID=legacy-file-app-id
UNIQUE_APP_KEY=prefixed-file-app-key
"""


@pytest.fixture
def env_file_content_with_filters() -> str:
    """Content for .env file with filter options."""
    return """
UNIQUE_AUTH_COMPANY_ID=file-company
UNIQUE_AUTH_USER_ID=file-user
UNIQUE_APP_ID=file-id
UNIQUE_APP_KEY=file-key
UNIQUE_APP_BASE_URL=https://api.file-example.com
UNIQUE_APP_ENDPOINT=/v1/file-endpoint
UNIQUE_APP_ENDPOINT_SECRET=file-endpoint-secret
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS=["file-assistant1", "file-assistant2"]
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE=["file-module1", "file-module2"]
"""


# ============================================================================
# Test Case Fixtures
# ============================================================================


@pytest.fixture
def base_url_aliases() -> List[str]:
    """All possible aliases for base_url field."""
    return [
        "unique_api_base_url",
        "base_url",
        "UNIQUE_API_BASE_URL",
        "BASE_URL",
    ]


@pytest.fixture
def app_key_aliases() -> List[str]:
    """All possible aliases for app key field."""
    return [
        "unique_app_key",
        "key",
        "UNIQUE_APP_KEY",
        "KEY",
        "API_KEY",
        "api_key",
    ]


@pytest.fixture
def app_id_aliases() -> List[str]:
    """All possible aliases for app id field."""
    return [
        "unique_app_id",
        "app_id",
        "UNIQUE_APP_ID",
        "APP_ID",
    ]


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def temp_env_file(tmp_path: Path) -> Path:
    """Temporary .env file path for testing."""
    return tmp_path / ".env"


@pytest.fixture
def caplog_handler():
    """Configure logging to capture warnings for default value tests."""
    return logging.getLogger()


# ============================================================================
# Schema Test Fixtures (Reusing existing base_chat_event_data)
# ============================================================================


@pytest.fixture
def base_user_message_json(base_chat_event_data: ChatEvent) -> str:
    """Base JSON for user message derived from existing base_chat_event_data."""
    return base_chat_event_data.payload.user_message.model_dump_json()


@pytest.fixture
def base_assistant_message_json(base_chat_event_data: ChatEvent) -> str:
    """Base JSON for assistant message derived from existing base_chat_event_data."""
    return base_chat_event_data.payload.assistant_message.model_dump_json()


@pytest.fixture
def base_event_payload_json(base_chat_event_data: ChatEvent) -> str:
    """Base JSON for event payload derived from existing base_chat_event_data."""
    # Create a payload with additional fields for testing
    payload_data = base_chat_event_data.payload.model_dump()
    payload_data.update(
        {
            "name": "unique.chat.external-module.chosen",
            "description": "Test description",
            "configuration": {"key": "value"},
            "text": "Optional text",
            "additionalParameters": {
                "translateToLanguage": "en",
                "contentIdToTranslate": "content_1234",
            },
        }
    )
    return json.dumps(payload_data)


@pytest.fixture
def base_event_json(base_chat_event_data: ChatEvent) -> str:
    """Base JSON for complete event derived from existing base_chat_event_data."""
    # Create a full event with additional fields for testing
    event_data = base_chat_event_data.model_dump()
    event_data.update(
        {
            "id": "event1",
            "userId": "user1",
            "companyId": "company1",
            "payload": {
                **event_data["payload"],
                "name": "test_module",
                "description": "Test description",
                "configuration": {"key": "value"},
                "text": "Optional text",
                "additionalParameters": {
                    "translateToLanguage": "en",
                    "contentIdToTranslate": "content_1234",
                },
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }
    )
    return json.dumps(event_data)


@pytest.fixture
def minimal_event_json(base_chat_event_data: ChatEvent) -> str:
    """Minimal event JSON for testing snake_case conversion."""
    event_data = base_chat_event_data.model_dump()
    event_data.update(
        {
            "id": "event1",
            "userId": "user1",
            "companyId": "company1",
            "payload": {
                **event_data["payload"],
                "name": "test_module",
                "description": "Test",
                "configuration": {},
            },
        }
    )
    return json.dumps(event_data)


# ============================================================================
# Chat Module Test Fixtures
# ============================================================================


@pytest.fixture
def base_chat_event() -> Event:
    """
    Base chat event fixture with all required fields.

    Returns:
        Event: A complete Event object for chat testing.
    """
    return Event(
        id="test-event-123",
        company_id="test_company_123",
        user_id="test_user_123",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        payload=EventPayload(
            name="test_module",
            description="Test module description",
            configuration={"test": "config"},
            assistant_message=EventAssistantMessage(
                id="assistant_msg_123",
                created_at="2024-01-01T12:00:00Z",
            ),
            user_message=EventUserMessage(
                id="user_msg_123",
                text="Hello, this is a test message",
                original_text="Hello, this is a test message",
                created_at="2024-01-01T12:00:00Z",
                language="english",
            ),
            chat_id="test_chat_123",
            assistant_id="test_assistant_123",
        ),
    )


@pytest.fixture
def base_chat_message() -> ChatMessage:
    """
    Base chat message fixture with all required fields.

    Returns:
        ChatMessage: A complete ChatMessage object for testing.
    """
    return ChatMessage(
        id="msg_123",
        chat_id="test_chat_123",
        role=ChatMessageRole.ASSISTANT,
        text="Test message content",
        content="Test message content",
        original_text="Test message content",
        created_at="2024-01-01T12:00:00Z",
        updated_at="2024-01-01T12:00:00Z",
        completed_at="2024-01-01T12:00:00Z",
        debug_info={"test": "debug"},
        references=[],
    )


@pytest.fixture
def base_user_message() -> ChatMessage:
    """
    Base user message fixture.

    Returns:
        ChatMessage: A user ChatMessage object for testing.
    """
    return ChatMessage(
        id="user_msg_123",
        chat_id="test_chat_123",
        role=ChatMessageRole.USER,
        text="User test message",
        content="User test message",
        original_text="User test message",
        created_at="2024-01-01T12:00:00Z",
        updated_at="2024-01-01T12:00:00Z",
        completed_at=None,
        debug_info=None,
        references=[],
    )


@pytest.fixture
def base_content_reference() -> ContentReference:
    """
    Base content reference fixture.

    Returns:
        ContentReference: A complete ContentReference object for testing.
    """
    return ContentReference(
        id="ref_123",
        message_id="msg_123",
        name="Test Document",
        url="https://example.com/test",
        sequence_number=1,
        source_id="src_123",
        source="web",
    )


@pytest.fixture
def base_content_chunk() -> ContentChunk:
    """
    Base content chunk fixture.

    Returns:
        ContentChunk: A complete ContentChunk object for testing.
    """
    return ContentChunk(
        id="chunk_123",
        chunk_id="chunk_123",
        key="test_key",
        order=1,
        text="Test chunk content",
    )


@pytest.fixture
def base_message_assessment() -> ChatMessageAssessment:
    """
    Base message assessment fixture.

    Returns:
        ChatMessageAssessment: A complete ChatMessageAssessment object for testing.
    """
    return ChatMessageAssessment(
        id="assessment_123",
        message_id="msg_123",
        status=ChatMessageAssessmentStatus.DONE,
        explanation="Test assessment explanation",
        label=ChatMessageAssessmentLabel.GREEN,
        type=ChatMessageAssessmentType.HALLUCINATION,
        is_visible=True,
        title="Test Assessment",
        created_at="2024-01-01T12:00:00Z",
        updated_at="2024-01-01T12:00:00Z",
    )


@pytest.fixture
def base_message_log() -> MessageLog:
    """
    Base message log fixture.

    Returns:
        MessageLog: A complete MessageLog object for testing.
    """
    return MessageLog(
        id="log_123",
        message_id="msg_123",
        status=MessageLogStatus.COMPLETED,
        details=MessageLogDetails(
            total_tokens=100,
            prompt_tokens=50,
            completion_tokens=50,
            model="test-model",
        ),
        uncited_references=MessageLogUncitedReferences(
            count=0,
            references=[],
        ),
        created_at="2024-01-01T12:00:00Z",
        updated_at="2024-01-01T12:00:00Z",
    )


@pytest.fixture
def base_message_execution() -> MessageExecution:
    """
    Base message execution fixture.

    Returns:
        MessageExecution: A complete MessageExecution object for testing.
    """
    return MessageExecution(
        id="execution_123",
        message_id="msg_123",
        type=MessageExecutionType.TOOL_CALL,
        status=MessageExecutionUpdateStatus.COMPLETED,
        result={"test": "result"},
        created_at="2024-01-01T12:00:00Z",
        updated_at="2024-01-01T12:00:00Z",
    )


@pytest.fixture
def sample_messages_list() -> list[ChatMessage]:
    """
    Sample list of chat messages for history testing.

    Returns:
        list[ChatMessage]: A list of ChatMessage objects representing a conversation.
    """
    return [
        ChatMessage(
            id="msg_1",
            chat_id="test_chat_123",
            role=ChatMessageRole.USER,
            text="Hello, how are you?",
            content="Hello, how are you?",
            original_text="Hello, how are you?",
            created_at="2024-01-01T12:00:00Z",
            updated_at="2024-01-01T12:00:00Z",
            completed_at=None,
            debug_info=None,
            references=[],
        ),
        ChatMessage(
            id="msg_2",
            chat_id="test_chat_123",
            role=ChatMessageRole.ASSISTANT,
            text="I'm doing well, thank you!",
            content="I'm doing well, thank you!",
            original_text="I'm doing well, thank you!",
            created_at="2024-01-01T12:01:00Z",
            updated_at="2024-01-01T12:01:00Z",
            completed_at="2024-01-01T12:01:00Z",
            debug_info={"tokens": 10},
            references=[],
        ),
        ChatMessage(
            id="msg_3",
            chat_id="test_chat_123",
            role=ChatMessageRole.USER,
            text="What's the weather like?",
            content="What's the weather like?",
            original_text="What's the weather like?",
            created_at="2024-01-01T12:02:00Z",
            updated_at="2024-01-01T12:02:00Z",
            completed_at=None,
            debug_info=None,
            references=[],
        ),
    ]


@pytest.fixture
def sample_sdk_message_data() -> dict:
    """
    Sample SDK message data that matches what the SDK returns.

    Returns:
        dict: Raw SDK message data with proper field names.
    """
    return {
        "id": "sdk_msg_123",
        "chatId": "test_chat_123",
        "text": "SDK test message",
        "role": "ASSISTANT",
        "originalText": "SDK test message",
        "createdAt": "2024-01-01T12:00:00Z",
        "updatedAt": "2024-01-01T12:00:00Z",
        "completedAt": "2024-01-01T12:00:00Z",
        "debugInfo": {"test": "debug"},
        "references": [],
    }


@pytest.fixture
def sample_sdk_messages_list() -> dict:
    """
    Sample SDK messages list response.

    Returns:
        dict: Raw SDK list response with proper structure.
    """
    return {
        "object": "list",
        "data": [
            {
                "id": "msg_1",
                "chatId": "test_chat_123",
                "text": "Hello, how are you?",
                "role": "USER",
                "originalText": "Hello, how are you?",
                "createdAt": "2024-01-01T12:00:00Z",
                "updatedAt": "2024-01-01T12:00:00Z",
                "completedAt": None,
                "debugInfo": None,
                "references": [],
            },
            {
                "id": "msg_2",
                "chatId": "test_chat_123",
                "text": "I'm doing well, thank you!",
                "role": "ASSISTANT",
                "originalText": "I'm doing well, thank you!",
                "createdAt": "2024-01-01T12:01:00Z",
                "updatedAt": "2024-01-01T12:01:00Z",
                "completedAt": "2024-01-01T12:01:00Z",
                "debugInfo": {"tokens": 10},
                "references": [],
            },
        ],
    }


@pytest.fixture
def sample_references_list() -> list[ContentReference]:
    """
    Sample list of content references for testing.

    Returns:
        list[ContentReference]: A list of ContentReference objects for testing.
    """
    return [
        ContentReference(
            id="ref_1",
            message_id="msg_1",
            name="Document 1",
            url="https://example.com/doc1",
            sequence_number=1,
            source_id="src_1",
            source="web",
        ),
        ContentReference(
            id="ref_2",
            message_id="msg_2",
            name="Document 2",
            url="https://example.com/doc2",
            sequence_number=2,
            source_id="src_2",
            source="pdf",
        ),
    ]


@pytest.fixture
def sample_content_chunks_list() -> list[ContentChunk]:
    """
    Sample list of content chunks for testing.

    Returns:
        list[ContentChunk]: A list of ContentChunk objects for testing.
    """
    return [
        ContentChunk(
            id="chunk_1",
            chunk_id="chunk_1",
            key="test_key_1",
            order=1,
            text="First chunk content",
        ),
        ContentChunk(
            id="chunk_2",
            chunk_id="chunk_2",
            key="test_key_2",
            order=2,
            text="Second chunk content",
        ),
    ]


# ============================================================================
# Evaluation Test Fixtures
# ============================================================================


@pytest.fixture
def base_evaluation_input() -> EvaluationMetricInput:
    """
    Base evaluation input fixture with all required fields.

    Returns:
        EvaluationMetricInput: A complete EvaluationMetricInput object for testing.
    """
    return EvaluationMetricInput(
        input_text="What is the capital of France?",
        context_texts=[
            "Paris is the capital of France.",
            "France is a country in Europe.",
        ],
        output_text="The capital of France is Paris.",
    )


@pytest.fixture
def base_evaluation_result() -> EvaluationMetricResult:
    """
    Base evaluation result fixture.

    Returns:
        EvaluationMetricResult: A complete EvaluationMetricResult object for testing.
    """
    return EvaluationMetricResult(
        name=EvaluationMetricName.HALLUCINATION,
        value="low",
        reason="The output is consistent with the provided context.",
        is_positive=True,
        user_info="Hallucination level: low",
    )


@pytest.fixture
def base_assessment_message() -> EvaluationAssessmentMessage:
    """
    Base assessment message fixture.

    Returns:
        EvaluationAssessmentMessage: A complete EvaluationAssessmentMessage object for testing.
    """
    return EvaluationAssessmentMessage(
        status=ChatMessageAssessmentStatus.DONE,
        explanation="No hallucination detected in the response",
        title="Hallucination Check",
        label=ChatMessageAssessmentLabel.GREEN,
        type=ChatMessageAssessmentType.HALLUCINATION,
    )


@pytest.fixture
def base_evaluation_config() -> EvaluationMetricConfig:
    """
    Base evaluation config fixture.

    Returns:
        EvaluationMetricConfig: A complete EvaluationMetricConfig object for testing.
    """
    return EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.HALLUCINATION,
        language_model=LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_35_TURBO_0125
        ),
    )


@pytest.fixture
def disabled_evaluation_config() -> EvaluationMetricConfig:
    """
    Disabled evaluation config fixture.

    Returns:
        EvaluationMetricConfig: A disabled EvaluationMetricConfig object for testing.
    """
    return EvaluationMetricConfig(
        enabled=False,
        name=EvaluationMetricName.HALLUCINATION,
    )


@pytest.fixture
def context_relevancy_evaluation_input() -> EvaluationMetricInput:
    """
    Context relevancy evaluation input fixture.

    Returns:
        EvaluationMetricInput: A complete input for context relevancy testing.
    """
    return EvaluationMetricInput(
        input_text="What is the weather like today?",
        context_texts=[
            "Today is sunny with 25°C temperature.",
            "The forecast shows clear skies.",
        ],
        output_text="Based on the current information, it's sunny and 25°C today.",
    )


@pytest.fixture
def context_relevancy_evaluation_result() -> EvaluationMetricResult:
    """
    Context relevancy evaluation result fixture.

    Returns:
        EvaluationMetricResult: A complete result for context relevancy testing.
    """
    return EvaluationMetricResult(
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        value="high",
        reason="The context is highly relevant to the input question.",
        is_positive=True,
        user_info="Relevancy level: high",
    )
