"""
Test fixtures for unique_deep_research tests.
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_chat_service() -> Mock:
    """Mock ChatService for testing."""
    mock_service = Mock()
    mock_service.get_full_history.return_value = []
    mock_service.get_full_history_async = AsyncMock(return_value=[])
    mock_service.complete_async = AsyncMock()
    mock_service.modify_assistant_message_async = AsyncMock()
    mock_service.create_message_log = Mock()
    mock_service.create_message_execution = Mock()
    mock_service.update_message_execution_async = AsyncMock()
    return mock_service


@pytest.fixture
def mock_content_service() -> Mock:
    """Mock ContentService for testing."""
    mock_service = Mock()
    mock_service.search_content_async = AsyncMock(return_value=[])
    return mock_service


@pytest.fixture
def mock_tool_progress_reporter() -> Mock:
    """Mock ToolProgressReporter for testing."""
    mock_reporter = Mock()
    mock_reporter.report_progress = Mock()
    return mock_reporter


@pytest.fixture
def mock_chat_event() -> Mock:
    """Mock ChatEvent for testing."""
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test research request"
    mock_event.payload.user_message.original_text = "Test research request"
    mock_event.payload.message_execution_id = None
    return mock_event


@pytest.fixture
def mock_language_model_info() -> Mock:
    """Mock LanguageModelInfo for testing."""
    mock_lmi = Mock()
    mock_lmi.name = "azure-gpt-4o-2024-1120"
    mock_lmi.max_tokens = 4000
    mock_lmi.temperature = 0.1
    return mock_lmi


@pytest.fixture
def sample_markdown_text() -> str:
    """Sample markdown text with links for testing."""
    return """
    This is a research report about AI.

    Here are some sources:
    - [OpenAI](https://openai.com) provides AI models
    - [Google Research](https://research.google.com) conducts AI research
    - [MIT AI Lab](https://www.csail.mit.edu) is a leading institution

    More information can be found at [AI Research](https://ai-research.com).
    """


@pytest.fixture
def sample_research_result() -> str:
    """Sample research result text for testing."""
    return """
    # AI Research Report

    Artificial Intelligence has evolved significantly. According to [OpenAI](https://openai.com), 
    modern AI systems can perform complex tasks. [Google Research](https://research.google.com) 
    has contributed to this field extensively.

    The future of AI looks promising with continued research and development.
    """


@pytest.fixture
def sample_citation_registry() -> Dict[str, Any]:
    """Sample citation registry for testing."""
    return {
        "https://openai.com": {
            "number": 1,
            "type": "web",
            "name": "OpenAI",
            "url": "https://openai.com",
            "source_id": "https://openai.com",
        },
        "https://research.google.com": {
            "number": 2,
            "type": "web",
            "name": "Google Research",
            "url": "https://research.google.com",
            "source_id": "https://research.google.com",
        },
    }
