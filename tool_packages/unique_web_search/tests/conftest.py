import asyncio

import pytest

from unique_web_search.schema import (
    Step,
    StepType,
    WebSearchPlan,
    WebSearchToolParameters,
)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_web_search_tool_parameters():
    """Sample WebSearchToolParameters for testing."""
    return WebSearchToolParameters(
        query="Python web scraping best practices", date_restrict="m1"
    )


@pytest.fixture
def sample_web_search_plan():
    """Sample WebSearchPlan for testing."""
    return WebSearchPlan(
        objective="Find information about Python web scraping",
        query_analysis="User wants to learn about web scraping techniques in Python",
        steps=[
            Step(
                step_type=StepType.SEARCH,
                objective="Search for Python web scraping tutorials",
                query_or_url="Python web scraping tutorial BeautifulSoup requests",
            ),
            Step(
                step_type=StepType.READ_URL,
                objective="Read detailed guide",
                query_or_url="https://realpython.com/python-web-scraping-practical-introduction/",
            ),
        ],
        expected_outcome="Comprehensive guide on Python web scraping techniques",
    )


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("JINA_API_KEY", "test-jina-key")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-firecrawl-key")
    monkeypatch.setenv("BING_SUBSCRIPTION_KEY", "test-bing-key")
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave-key")
