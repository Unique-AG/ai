from unique_web_search.schema import (
    Step,
    StepType,
    WebSearchPlan,
    WebSearchToolParameters,
)


class TestWebSearchToolParameters:
    """Test cases for WebSearchToolParameters model."""

    def test_valid_parameters(self):
        """Test creating valid WebSearchToolParameters."""
        params = WebSearchToolParameters(
            query="Python web scraping tutorial", date_restrict="m1"
        )

        assert params.query == "Python web scraping tutorial"
        assert params.date_restrict == "m1"

    def test_parameters_without_date_restrict(self):
        """Test creating parameters without date restriction."""
        params = WebSearchToolParameters(query="Python tutorial", date_restrict=None)

        assert params.query == "Python tutorial"
        assert params.date_restrict is None

    def test_empty_query_validation(self):
        """Test that query validation works as expected."""
        params = WebSearchToolParameters(query="", date_restrict=None)
        assert params.query == ""

    def test_from_tool_parameter_query_description(self):
        """Test creating model with custom query description."""
        CustomParams = WebSearchToolParameters.from_tool_parameter_query_description(
            query_description="Custom query description",
            date_restrict_description="Custom date restrict description",
        )

        # Test that we can create an instance
        params = CustomParams(query="test query", date_restrict="d1")

        assert params.query == "test query"
        assert params.date_restrict == "d1"
        assert CustomParams.__name__ == "WebSearchToolParameters"

    def test_from_tool_parameter_query_description_none_date_restrict(self):
        """Test creating model with None date restrict description."""
        CustomParams = WebSearchToolParameters.from_tool_parameter_query_description(
            query_description="Custom query description", date_restrict_description=None
        )

        params = CustomParams(query="test query", date_restrict=None)

        assert params.query == "test query"
        assert params.date_restrict is None


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
