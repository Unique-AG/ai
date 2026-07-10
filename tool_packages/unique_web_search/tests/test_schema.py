import pytest

from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.executors.v2.schema import Step, StepType, WebSearchPlan
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)

_SAMPLE_RESULT_PAYLOAD = {
    "url": "https://example.com",
    "title": "Example",
    "snippet": "An example page",
    "content": "",
}


class TestWebSearchResults:
    """Tests for WebSearchResults validation aliases."""

    @pytest.mark.ai
    @pytest.mark.parametrize("key", ["results", "curated"])
    def test_model_validate__accepts_results_or_curated_key(self, key: str) -> None:
        """
        Purpose: Verify WebSearchResults accepts both `results` and `curated` JSON keys.
        Why this matters: Custom APIs and the search proxy use different wrapper field names.
        Setup summary: Validate JSON with one key; assert `.results` is populated correctly.
        """
        # Act
        parsed = WebSearchResults.model_validate({key: [_SAMPLE_RESULT_PAYLOAD]})

        # Assert
        assert len(parsed.results) == 1
        assert parsed.results[0] == WebSearchResult.model_validate(
            _SAMPLE_RESULT_PAYLOAD
        )

    @pytest.mark.ai
    def test_model_dump__serializes_as_results_key(self) -> None:
        """
        Purpose: Verify serialized output always uses the `results` key.
        Why this matters: Downstream consumers expect a stable wire format.
        Setup summary: Build WebSearchResults; assert model_dump keys and values.
        """
        # Arrange
        result = WebSearchResult.model_validate(_SAMPLE_RESULT_PAYLOAD)
        web_search_results = WebSearchResults(results=[result])

        # Act
        dumped = web_search_results.model_dump()

        # Assert
        assert list(dumped.keys()) == ["results"]
        assert dumped["results"][0] == _SAMPLE_RESULT_PAYLOAD


class TestWebSearchToolParameters:
    """Test cases for WebSearchToolParameters model."""

    def test_valid_parameters(self):
        """Test creating valid WebSearchToolParameters."""
        params = WebSearchToolParameters(query="Python web scraping tutorial")

        assert params.query == "Python web scraping tutorial"

    def test_empty_query_validation(self):
        """Test that query validation works as expected."""
        params = WebSearchToolParameters(query="")
        assert params.query == ""

    def test_with_exposed_params_from_google_config(self):
        """Test grafting exposed Google knobs onto the V1 tool model."""
        from unique_search_proxy_core.search_engines.google.schema import (
            ExposableStrOrNone,
            GoogleConfig,
        )

        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value=None),
        )
        CustomParams = WebSearchToolParameters.with_exposed_params(
            config.exposed_params_model()
        )

        params = CustomParams(query="test query", dateRestrict="d1")

        assert params.query == "test query"
        assert params.date_restrict == "d1"
        assert CustomParams.__name__ == "WebSearchToolParameters"

    def test_with_exposed_params_none_returns_base(self):
        """Test that with_exposed_params(None) returns the base class."""
        assert WebSearchToolParameters.with_exposed_params(None) is WebSearchToolParameters


class TestStepType:
    """Test cases for StepType enum."""

    def test_step_type_values(self):
        """Test StepType enum values."""
        assert StepType.SEARCH == "search"
        assert StepType.READ_URL == "read_url"

    def test_step_type_membership(self):
        """Test StepType membership."""
        assert "search" in StepType
        assert "read_url" in StepType
        assert "invalid" not in StepType


class TestStep:
    """Test cases for Step model."""

    def test_valid_search_step(self):
        """Test creating a valid search step."""
        step = Step(
            step_type=StepType.SEARCH,
            objective="Find Python tutorials",
            query_or_url="Python tutorial beginners guide",
        )

        assert step.step_type == StepType.SEARCH
        assert step.objective == "Find Python tutorials"
        assert step.query_or_url == "Python tutorial beginners guide"

    def test_valid_read_url_step(self):
        """Test creating a valid read URL step."""
        step = Step(
            step_type=StepType.READ_URL,
            objective="Read detailed tutorial",
            query_or_url="https://realpython.com/python-web-scraping-practical-introduction/",
        )

        assert step.step_type == StepType.READ_URL
        assert step.objective == "Read detailed tutorial"
        assert (
            step.query_or_url
            == "https://realpython.com/python-web-scraping-practical-introduction/"
        )

    def test_search_step_with_string_literal(self):
        """Test creating search step with string literal."""
        step = Step(
            step_type=StepType.SEARCH,
            objective="Search for information",
            query_or_url="machine learning basics",
        )

        assert step.step_type == StepType.SEARCH
        assert step.objective == "Search for information"
        assert step.query_or_url == "machine learning basics"

    def test_read_url_step_with_string_literal(self):
        """Test creating read URL step with string literal."""
        step = Step(
            step_type=StepType.READ_URL,
            objective="Read specific page",
            query_or_url="https://example.com/article",
        )

        assert step.step_type == StepType.READ_URL
        assert step.objective == "Read specific page"
        assert step.query_or_url == "https://example.com/article"


class TestWebSearchPlan:
    """Test cases for WebSearchPlan model."""

    def test_valid_plan(self):
        """Test creating a valid WebSearchPlan."""
        plan = WebSearchPlan(
            objective="Learn about Python web scraping",
            query_analysis="User wants comprehensive information about web scraping in Python",
            steps=[
                Step(
                    step_type=StepType.SEARCH,
                    objective="Find general tutorials",
                    query_or_url="Python web scraping tutorial BeautifulSoup",
                ),
                Step(
                    step_type=StepType.READ_URL,
                    objective="Read detailed guide",
                    query_or_url="https://realpython.com/python-web-scraping-practical-introduction/",
                ),
            ],
            expected_outcome="Comprehensive understanding of Python web scraping techniques",
        )

        assert plan.objective == "Learn about Python web scraping"
        assert (
            plan.query_analysis
            == "User wants comprehensive information about web scraping in Python"
        )
        assert len(plan.steps) == 2
        assert plan.steps[0].step_type == StepType.SEARCH
        assert plan.steps[1].step_type == StepType.READ_URL
        assert (
            plan.expected_outcome
            == "Comprehensive understanding of Python web scraping techniques"
        )

    def test_plan_with_single_step(self):
        """Test creating a plan with a single step."""
        plan = WebSearchPlan(
            objective="Quick search",
            query_analysis="Simple information lookup",
            steps=[
                Step(
                    step_type=StepType.SEARCH,
                    objective="Find information",
                    query_or_url="Python basics",
                )
            ],
            expected_outcome="Basic Python information",
        )

        assert len(plan.steps) == 1
        assert plan.steps[0].step_type == StepType.SEARCH

    def test_plan_with_multiple_search_steps(self):
        """Test creating a plan with multiple search steps."""
        plan = WebSearchPlan(
            objective="Research machine learning",
            query_analysis="User needs comprehensive ML information",
            steps=[
                Step(
                    step_type=StepType.SEARCH,
                    objective="Find ML basics",
                    query_or_url="machine learning introduction",
                ),
                Step(
                    step_type=StepType.SEARCH,
                    objective="Find advanced topics",
                    query_or_url="advanced machine learning algorithms",
                ),
                Step(
                    step_type=StepType.SEARCH,
                    objective="Find practical examples",
                    query_or_url="machine learning projects examples",
                ),
            ],
            expected_outcome="Complete understanding of machine learning",
        )

        assert len(plan.steps) == 3
        assert all(step.step_type == StepType.SEARCH for step in plan.steps)

    def test_plan_with_multiple_read_url_steps(self):
        """Test creating a plan with multiple read URL steps."""
        plan = WebSearchPlan(
            objective="Read specific articles",
            query_analysis="User wants to read specific resources",
            steps=[
                Step(
                    step_type=StepType.READ_URL,
                    objective="Read first article",
                    query_or_url="https://example.com/article1",
                ),
                Step(
                    step_type=StepType.READ_URL,
                    objective="Read second article",
                    query_or_url="https://example.com/article2",
                ),
            ],
            expected_outcome="Information from specific articles",
        )

        assert len(plan.steps) == 2
        assert all(step.step_type == StepType.READ_URL for step in plan.steps)

    def test_empty_steps_list(self):
        """Test that empty steps list is allowed."""
        plan = WebSearchPlan(
            objective="Empty plan",
            query_analysis="No steps needed",
            steps=[],
            expected_outcome="No outcome",
        )

        assert len(plan.steps) == 0

    def test_plan_serialization(self):
        """Test that WebSearchPlan can be serialized to dict."""
        plan = WebSearchPlan(
            objective="Test objective",
            query_analysis="Test analysis",
            steps=[
                Step(
                    step_type=StepType.SEARCH,
                    objective="Search step",
                    query_or_url="test query",
                )
            ],
            expected_outcome="Test outcome",
        )

        plan_dict = plan.model_dump()

        assert plan_dict["objective"] == "Test objective"
        assert plan_dict["query_analysis"] == "Test analysis"
        assert len(plan_dict["steps"]) == 1
        assert plan_dict["steps"][0]["step_type"] == "search"
        assert plan_dict["expected_outcome"] == "Test outcome"

    def test_plan_deserialization(self):
        """Test that WebSearchPlan can be deserialized from dict."""
        plan_dict = {
            "objective": "Test objective",
            "query_analysis": "Test analysis",
            "steps": [
                {
                    "step_type": "search",
                    "objective": "Search step",
                    "query_or_url": "test query",
                }
            ],
            "expected_outcome": "Test outcome",
        }

        plan = WebSearchPlan.model_validate(plan_dict)

        assert plan.objective == "Test objective"
        assert plan.query_analysis == "Test analysis"
        assert len(plan.steps) == 1
        assert plan.steps[0].step_type == StepType.SEARCH
        assert plan.expected_outcome == "Test outcome"
