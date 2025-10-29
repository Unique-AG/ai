import pytest

from unique_web_search.schema import (
    Step,
    StepType,
    WebSearchPlan,
    WebSearchToolParameters,
)


class TestWebSearchToolParameters:
    """Test cases for WebSearchToolParameters model."""

    @pytest.mark.ai
    def test_web_search_tool_parameters__creates_with_query_and_date__when_both_provided(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchToolParameters creates correctly with query and date restriction.
        Why this matters: Ensures search parameters are properly structured for time-bounded queries.
        Setup summary: Create WebSearchToolParameters with query and date_restrict, assert both values stored.
        """
        # Arrange
        query: str = "Python web scraping tutorial"
        date_restrict: str = "m1"

        # Act
        params: WebSearchToolParameters = WebSearchToolParameters(
            query=query,
            date_restrict=date_restrict,
        )

        # Assert
        assert params.query == "Python web scraping tutorial"
        assert params.date_restrict == "m1"

    @pytest.mark.ai
    def test_web_search_tool_parameters__creates_without_date__when_date_restrict_none(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchToolParameters creates correctly without date restriction.
        Why this matters: Ensures search parameters support queries without time constraints.
        Setup summary: Create WebSearchToolParameters with query and None date_restrict, assert values stored.
        """
        # Arrange
        query: str = "Python tutorial"

        # Act
        params: WebSearchToolParameters = WebSearchToolParameters(
            query=query,
            date_restrict=None,
        )

        # Assert
        assert params.query == "Python tutorial"
        assert params.date_restrict is None

    @pytest.mark.ai
    def test_web_search_tool_parameters__accepts_empty_query__when_empty_string_provided(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchToolParameters accepts empty query string without validation error.
        Why this matters: Ensures flexible parameter handling for edge cases.
        Setup summary: Create WebSearchToolParameters with empty query, assert query stored as empty string.
        """
        # Arrange
        query: str = ""

        # Act
        params: WebSearchToolParameters = WebSearchToolParameters(
            query=query,
            date_restrict=None,
        )

        # Assert
        assert params.query == ""

    @pytest.mark.ai
    def test_web_search_tool_parameters__creates_custom_class__when_from_tool_parameter_query_description_called(
        self,
    ) -> None:
        """
        Purpose: Verify factory method creates custom parameter class with custom descriptions.
        Why this matters: Enables dynamic parameter schema customization for different use cases.
        Setup summary: Call factory method with custom descriptions, create instance, assert class name and values.
        """
        # Arrange
        query_description: str = "Custom query description"
        date_restrict_description: str = "Custom date restrict description"

        # Act
        CustomParams = WebSearchToolParameters.from_tool_parameter_query_description(
            query_description=query_description,
            date_restrict_description=date_restrict_description,
        )
        params: WebSearchToolParameters = CustomParams(
            query="test query",
            date_restrict="d1",
        )

        # Assert
        assert params.query == "test query"
        assert params.date_restrict == "d1"
        assert CustomParams.__name__ == "WebSearchToolParameters"

    @pytest.mark.ai
    def test_web_search_tool_parameters__creates_custom_class_with_none_date__when_date_restrict_description_none(
        self,
    ) -> None:
        """
        Purpose: Verify factory method creates custom parameter class when date restriction description is None.
        Why this matters: Ensures flexibility in parameter schema customization.
        Setup summary: Call factory method with None date_restrict_description, create instance, assert values.
        """
        # Arrange
        query_description: str = "Custom query description"

        # Act
        CustomParams = WebSearchToolParameters.from_tool_parameter_query_description(
            query_description=query_description,
            date_restrict_description=None,
        )
        params: WebSearchToolParameters = CustomParams(
            query="test query",
            date_restrict=None,
        )

        # Assert
        assert params.query == "test query"
        assert params.date_restrict is None


class TestStepType:
    """Test cases for StepType enum."""

    @pytest.mark.ai
    def test_step_type__has_expected_values__for_search_and_read_url(self) -> None:
        """
        Purpose: Verify StepType enum contains expected values for search and read operations.
        Why this matters: Ensures step type constants are correctly defined.
        Setup summary: Assert StepType constants equal expected string values.
        """
        # Arrange & Act & Assert
        assert StepType.SEARCH == "search"
        assert StepType.READ_URL == "read_url"

    @pytest.mark.ai
    def test_step_type__validates_membership__for_valid_and_invalid_names(self) -> None:
        """
        Purpose: Verify StepType membership operator correctly identifies valid and invalid names.
        Why this matters: Ensures type safety when checking step type validity.
        Setup summary: Assert valid names are in StepType, invalid name is not.
        """
        # Arrange & Act & Assert
        assert "search" in StepType
        assert "read_url" in StepType
        assert "invalid" not in StepType


class TestStep:
    """Test cases for Step model."""

    @pytest.mark.ai
    def test_step__creates_search_step__with_search_type_and_query(self) -> None:
        """
        Purpose: Verify Step model creates correctly for search operations.
        Why this matters: Ensures search steps are properly structured in web search plans.
        Setup summary: Create Step with SEARCH type, objective, and query, assert all fields correct.
        """
        # Arrange
        step_type: StepType = StepType.SEARCH
        objective: str = "Find Python tutorials"
        query_or_url: str = "Python tutorial beginners guide"

        # Act
        step: Step = Step(
            step_type=step_type,
            objective=objective,
            query_or_url=query_or_url,
        )

        # Assert
        assert step.step_type == StepType.SEARCH
        assert step.objective == "Find Python tutorials"
        assert step.query_or_url == "Python tutorial beginners guide"

    @pytest.mark.ai
    def test_step__creates_read_url_step__with_read_url_type_and_url(self) -> None:
        """
        Purpose: Verify Step model creates correctly for URL reading operations.
        Why this matters: Ensures URL reading steps are properly structured in web search plans.
        Setup summary: Create Step with READ_URL type, objective, and URL, assert all fields correct.
        """
        # Arrange
        step_type: StepType = StepType.READ_URL
        objective: str = "Read detailed tutorial"
        query_or_url: str = (
            "https://realpython.com/python-web-scraping-practical-introduction/"
        )

        # Act
        step: Step = Step(
            step_type=step_type,
            objective=objective,
            query_or_url=query_or_url,
        )

        # Assert
        assert step.step_type == StepType.READ_URL
        assert step.objective == "Read detailed tutorial"
        assert (
            step.query_or_url
            == "https://realpython.com/python-web-scraping-practical-introduction/"
        )

    @pytest.mark.ai
    def test_step__creates_search_step__with_string_query(self) -> None:
        """
        Purpose: Verify Step model accepts string query for search operations.
        Why this matters: Ensures search steps can use text queries as input.
        Setup summary: Create Step with SEARCH type and string query, assert query stored correctly.
        """
        # Arrange
        step_type: StepType = StepType.SEARCH
        objective: str = "Search for information"
        query_or_url: str = "machine learning basics"

        # Act
        step: Step = Step(
            step_type=step_type,
            objective=objective,
            query_or_url=query_or_url,
        )

        # Assert
        assert step.step_type == StepType.SEARCH
        assert step.objective == "Search for information"
        assert step.query_or_url == "machine learning basics"

    @pytest.mark.ai
    def test_step__creates_read_url_step__with_url_string(self) -> None:
        """
        Purpose: Verify Step model accepts URL string for read operations.
        Why this matters: Ensures URL reading steps can use URL strings as input.
        Setup summary: Create Step with READ_URL type and URL string, assert URL stored correctly.
        """
        # Arrange
        step_type: StepType = StepType.READ_URL
        objective: str = "Read specific page"
        query_or_url: str = "https://example.com/article"

        # Act
        step: Step = Step(
            step_type=step_type,
            objective=objective,
            query_or_url=query_or_url,
        )

        # Assert
        assert step.step_type == StepType.READ_URL
        assert step.objective == "Read specific page"
        assert step.query_or_url == "https://example.com/article"


class TestWebSearchPlan:
    """Test cases for WebSearchPlan model."""

    @pytest.mark.ai
    def test_web_search_plan__creates_with_multiple_steps__when_initialized(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchPlan creates correctly with mixed search and read URL steps.
        Why this matters: Ensures search plans support complex multi-step workflows.
        Setup summary: Create WebSearchPlan with objective, analysis, multiple steps, and outcome, assert structure.
        """
        # Arrange
        objective: str = "Learn about Python web scraping"
        query_analysis: str = (
            "User wants comprehensive information about web scraping in Python"
        )
        steps: list[Step] = [
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
        ]
        expected_outcome: str = (
            "Comprehensive understanding of Python web scraping techniques"
        )

        # Act
        plan: WebSearchPlan = WebSearchPlan(
            objective=objective,
            query_analysis=query_analysis,
            steps=steps,
            expected_outcome=expected_outcome,
        )

        # Assert
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

    @pytest.mark.ai
    def test_web_search_plan__creates_with_single_step__when_one_step_provided(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchPlan creates correctly with single step.
        Why this matters: Ensures search plans support simple single-step workflows.
        Setup summary: Create WebSearchPlan with single step, assert step count and type correct.
        """
        # Arrange
        objective: str = "Quick search"
        query_analysis: str = "Simple information lookup"
        steps: list[Step] = [
            Step(
                step_type=StepType.SEARCH,
                objective="Find information",
                query_or_url="Python basics",
            ),
        ]
        expected_outcome: str = "Basic Python information"

        # Act
        plan: WebSearchPlan = WebSearchPlan(
            objective=objective,
            query_analysis=query_analysis,
            steps=steps,
            expected_outcome=expected_outcome,
        )

        # Assert
        assert len(plan.steps) == 1
        assert plan.steps[0].step_type == StepType.SEARCH

    @pytest.mark.ai
    def test_web_search_plan__creates_with_multiple_search_steps__when_all_steps_are_search(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchPlan creates correctly with multiple search steps.
        Why this matters: Ensures search plans support multiple sequential search operations.
        Setup summary: Create WebSearchPlan with multiple search steps, assert all steps are search type.
        """
        # Arrange
        objective: str = "Research machine learning"
        query_analysis: str = "User needs comprehensive ML information"
        steps: list[Step] = [
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
        ]
        expected_outcome: str = "Complete understanding of machine learning"

        # Act
        plan: WebSearchPlan = WebSearchPlan(
            objective=objective,
            query_analysis=query_analysis,
            steps=steps,
            expected_outcome=expected_outcome,
        )

        # Assert
        assert len(plan.steps) == 3
        assert all(step.step_type == StepType.SEARCH for step in plan.steps)

    @pytest.mark.ai
    def test_web_search_plan__creates_with_multiple_read_url_steps__when_all_steps_are_read_url(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchPlan creates correctly with multiple read URL steps.
        Why this matters: Ensures search plans support multiple sequential URL reading operations.
        Setup summary: Create WebSearchPlan with multiple read URL steps, assert all steps are read URL type.
        """
        # Arrange
        objective: str = "Read specific articles"
        query_analysis: str = "User wants to read specific resources"
        steps: list[Step] = [
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
        ]
        expected_outcome: str = "Information from specific articles"

        # Act
        plan: WebSearchPlan = WebSearchPlan(
            objective=objective,
            query_analysis=query_analysis,
            steps=steps,
            expected_outcome=expected_outcome,
        )

        # Assert
        assert len(plan.steps) == 2
        assert all(step.step_type == StepType.READ_URL for step in plan.steps)

    @pytest.mark.ai
    def test_web_search_plan__creates_with_empty_steps__when_steps_list_empty(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchPlan creates correctly with empty steps list.
        Why this matters: Ensures search plans support edge case of no steps.
        Setup summary: Create WebSearchPlan with empty steps list, assert steps count is zero.
        """
        # Arrange
        objective: str = "Empty plan"
        query_analysis: str = "No steps needed"
        steps: list[Step] = []
        expected_outcome: str = "No outcome"

        # Act
        plan: WebSearchPlan = WebSearchPlan(
            objective=objective,
            query_analysis=query_analysis,
            steps=steps,
            expected_outcome=expected_outcome,
        )

        # Assert
        assert len(plan.steps) == 0

    @pytest.mark.ai
    def test_web_search_plan__serializes_to_dict__when_model_dump_called(self) -> None:
        """
        Purpose: Verify WebSearchPlan serializes correctly to dictionary format.
        Why this matters: Ensures proper data serialization for API responses and storage.
        Setup summary: Create WebSearchPlan, call model_dump(), assert dictionary structure and values.
        """
        # Arrange
        plan: WebSearchPlan = WebSearchPlan(
            objective="Test objective",
            query_analysis="Test analysis",
            steps=[
                Step(
                    step_type=StepType.SEARCH,
                    objective="Search step",
                    query_or_url="test query",
                ),
            ],
            expected_outcome="Test outcome",
        )

        # Act
        plan_dict: dict = plan.model_dump()

        # Assert
        assert plan_dict["objective"] == "Test objective"
        assert plan_dict["query_analysis"] == "Test analysis"
        assert len(plan_dict["steps"]) == 1
        assert plan_dict["steps"][0]["step_type"] == "search"
        assert plan_dict["expected_outcome"] == "Test outcome"

    @pytest.mark.ai
    def test_web_search_plan__deserializes_from_dict__when_model_validate_called(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchPlan deserializes correctly from dictionary format.
        Why this matters: Ensures proper data deserialization from API requests and storage.
        Setup summary: Create plan dictionary, call model_validate(), assert plan structure and values.
        """
        # Arrange
        plan_dict: dict = {
            "objective": "Test objective",
            "query_analysis": "Test analysis",
            "steps": [
                {
                    "step_type": "search",
                    "objective": "Search step",
                    "query_or_url": "test query",
                },
            ],
            "expected_outcome": "Test outcome",
        }

        # Act
        plan: WebSearchPlan = WebSearchPlan.model_validate(plan_dict)

        # Assert
        assert plan.objective == "Test objective"
        assert plan.query_analysis == "Test analysis"
        assert len(plan.steps) == 1
        assert plan.steps[0].step_type == StepType.SEARCH
        assert plan.expected_outcome == "Test outcome"
