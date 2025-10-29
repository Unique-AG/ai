import pytest
from pydantic import ValidationError
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
    LanguageModelTokenLimits,
    ModelCapabilities,
)

from unique_web_search.config import (
    AnswerGenerationConfig,
    ExperimentalFeatures,
    QueryRefinementConfig,
    WebSearchConfig,
    WebSearchToolParametersConfig,
    WebSearchV1,
    WebSearchV2,
)
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawlerConfig
from unique_web_search.services.executors.web_search_v1_executor import RefineQueryMode
from unique_web_search.services.search_engine.base import SearchEngineType
from unique_web_search.services.search_engine.google import GoogleConfig


class TestAnswerGenerationConfig:
    """Test cases for AnswerGenerationConfig."""

    @pytest.mark.ai
    def test_answer_generation_config_defaults(self) -> None:
        """
        Purpose: Verify AnswerGenerationConfig creates with expected default values.
        Why this matters: Ensures proper default configuration for answer generation.
        Setup summary: Create AnswerGenerationConfig with no parameters, assert default values.
        """
        # Arrange & Act
        config = AnswerGenerationConfig()

        # Assert
        assert config.limit_token_sources == 10000
        assert config.max_chunks_to_consider == 20
        assert config.number_history_interactions_included == 2

    @pytest.mark.ai
    def test_answer_generation_config_custom_values(self) -> None:
        """
        Purpose: Verify AnswerGenerationConfig accepts and stores custom values.
        Why this matters: Ensures flexibility in configuring answer generation parameters.
        Setup summary: Create AnswerGenerationConfig with custom values, assert all values stored correctly.
        """
        # Arrange
        limit_token_sources: int = 15000
        max_chunks_to_consider: int = 30
        number_history_interactions_included: int = 5

        # Act
        config = AnswerGenerationConfig(
            limit_token_sources=limit_token_sources,
            max_chunks_to_consider=max_chunks_to_consider,
            number_history_interactions_included=number_history_interactions_included,
        )

        # Assert
        assert config.limit_token_sources == 15000
        assert config.max_chunks_to_consider == 30
        assert config.number_history_interactions_included == 5


class TestWebSearchV1:
    """Test cases for WebSearchV1 configuration."""

    @pytest.mark.ai
    def test_web_search_v1_defaults(self) -> None:
        """
        Purpose: Verify WebSearchV1 creates with expected default values.
        Why this matters: Ensures proper default configuration for V1 search executor.
        Setup summary: Create WebSearchV1 with no parameters, assert default values.
        """
        # Arrange & Act
        config = WebSearchV1()

        # Assert
        assert config.refine_query_mode == RefineQueryMode.BASIC
        assert config.max_queries == 5

    @pytest.mark.ai
    def test_web_search_v1_custom_values(self) -> None:
        """
        Purpose: Verify WebSearchV1 accepts and stores custom configuration values.
        Why this matters: Ensures flexibility in configuring V1 search executor behavior.
        Setup summary: Create WebSearchV1 with custom values, assert all values stored correctly.
        """
        # Arrange
        refine_query_mode: RefineQueryMode = RefineQueryMode.ADVANCED
        max_queries: int = 10

        # Act
        config = WebSearchV1(
            refine_query_mode=refine_query_mode,
            max_queries=max_queries,
        )

        # Assert
        assert config.refine_query_mode == RefineQueryMode.ADVANCED
        assert config.max_queries == 10


class TestWebSearchV2:
    """Test cases for WebSearchV2 configuration."""

    @pytest.mark.ai
    def test_web_search_v2_enabled(self) -> None:
        """
        Purpose: Verify WebSearchV2 creates correctly when enabled with custom values.
        Why this matters: Ensures proper configuration for V2 search executor when enabled.
        Setup summary: Create WebSearchV2 with enabled=True and custom values, assert all values stored.
        """
        # Arrange
        enabled: bool = True
        max_steps: int = 10
        tool_description: str = "Custom V2 description"

        # Act
        config = WebSearchV2(
            enabled=enabled,
            max_steps=max_steps,
            tool_description=tool_description,
        )

        # Assert
        assert config.enabled is True
        assert config.max_steps == 10
        assert config.tool_description == "Custom V2 description"

    @pytest.mark.ai
    def test_web_search_v2_tool_descriptions(self) -> None:
        """
        Purpose: Verify WebSearchV2 accepts and stores custom tool descriptions.
        Why this matters: Ensures flexibility in customizing tool descriptions for V2 executor.
        Setup summary: Create WebSearchV2 with custom tool descriptions, assert descriptions stored correctly.
        """
        # Arrange
        tool_description: str = "Custom tool description"
        tool_description_for_system_prompt: str = "Custom system prompt description"

        # Act
        config = WebSearchV2(
            tool_description=tool_description,
            tool_description_for_system_prompt=tool_description_for_system_prompt,
        )

        # Assert
        assert config.tool_description == "Custom tool description"
        assert (
            config.tool_description_for_system_prompt
            == "Custom system prompt description"
        )


class TestExperimentalFeatures:
    """Test cases for ExperimentalFeatures configuration."""

    @pytest.mark.ai
    def test_experimental_features_defaults(self) -> None:
        """
        Purpose: Verify ExperimentalFeatures creates with default V1 and V2 configurations.
        Why this matters: Ensures proper default configuration for experimental search features.
        Setup summary: Create ExperimentalFeatures with no parameters, assert V1 and V2 defaults present.
        """
        # Arrange & Act
        config = ExperimentalFeatures()

        # Assert
        assert isinstance(config.v1_mode, WebSearchV1)
        assert isinstance(config.v2_mode, WebSearchV2)
        assert config.v2_mode.enabled is False

    @pytest.mark.ai
    def test_experimental_features_custom_v1(self) -> None:
        """
        Purpose: Verify ExperimentalFeatures accepts and stores custom V1 configuration.
        Why this matters: Ensures flexibility in configuring V1 search executor behavior.
        Setup summary: Create WebSearchV1 with custom values, pass to ExperimentalFeatures, assert values stored.
        """
        # Arrange
        v1_config = WebSearchV1(
            refine_query_mode=RefineQueryMode.ADVANCED, max_queries=8
        )

        # Act
        config = ExperimentalFeatures(v1_mode=v1_config)

        # Assert
        assert config.v1_mode.refine_query_mode == RefineQueryMode.ADVANCED
        assert config.v1_mode.max_queries == 8

    @pytest.mark.ai
    def test_experimental_features_custom_v2(self) -> None:
        """
        Purpose: Verify ExperimentalFeatures accepts and stores custom V2 configuration.
        Why this matters: Ensures flexibility in configuring V2 search executor behavior.
        Setup summary: Create WebSearchV2 with custom values, pass to ExperimentalFeatures, assert values stored.
        """
        # Arrange
        v2_config = WebSearchV2(enabled=True, max_steps=7)

        # Act
        config = ExperimentalFeatures(v2_mode=v2_config)

        # Assert
        assert config.v2_mode.enabled is True
        assert config.v2_mode.max_steps == 7


class TestQueryRefinementConfig:
    """Test cases for QueryRefinementConfig."""

    @pytest.mark.ai
    def test_query_refinement_config_defaults(self) -> None:
        """
        Purpose: Verify QueryRefinementConfig creates with enabled state and default system prompt.
        Why this matters: Ensures proper default configuration for query refinement feature.
        Setup summary: Create QueryRefinementConfig with no parameters, assert enabled=True and prompt exists.
        """
        # Arrange & Act
        config = QueryRefinementConfig()

        # Assert
        assert config.enabled is True
        assert len(config.system_prompt) > 0

    @pytest.mark.ai
    def test_query_refinement_config_disabled(self) -> None:
        """
        Purpose: Verify QueryRefinementConfig accepts disabled state and custom system prompt.
        Why this matters: Ensures flexibility in disabling query refinement and customizing prompts.
        Setup summary: Create QueryRefinementConfig with enabled=False and custom prompt, assert values stored.
        """
        # Arrange
        custom_prompt: str = "Custom system prompt"

        # Act
        config = QueryRefinementConfig(enabled=False, system_prompt=custom_prompt)

        # Assert
        assert config.enabled is False
        assert config.system_prompt == "Custom system prompt"


class TestWebSearchToolParametersConfig:
    """Test cases for WebSearchToolParametersConfig."""

    @pytest.mark.ai
    def test_tool_parameters_config_defaults(self) -> None:
        """
        Purpose: Verify WebSearchToolParametersConfig creates with default query and date descriptions.
        Why this matters: Ensures proper default descriptions for tool parameters.
        Setup summary: Create WebSearchToolParametersConfig with no parameters, assert default descriptions present.
        """
        # Arrange & Act
        config = WebSearchToolParametersConfig()

        # Assert
        assert "search query" in config.query_description.lower()
        assert len(config.date_restrict_description) > 0

    @pytest.mark.ai
    def test_tool_parameters_config_custom(self) -> None:
        """
        Purpose: Verify WebSearchToolParametersConfig accepts and stores custom descriptions.
        Why this matters: Ensures flexibility in customizing tool parameter descriptions.
        Setup summary: Create WebSearchToolParametersConfig with custom descriptions, assert values stored correctly.
        """
        # Arrange
        query_desc: str = "Custom query description"
        date_desc: str = "Custom date restriction description"

        # Act
        config = WebSearchToolParametersConfig(
            query_description=query_desc,
            date_restrict_description=date_desc,
        )

        # Assert
        assert config.query_description == "Custom query description"
        assert config.date_restrict_description == "Custom date restriction description"


class TestWebSearchConfig:
    """Test cases for main WebSearchConfig."""

    @pytest.fixture
    def mock_language_model_info(self):
        """Mock LanguageModelInfo with structured output capability."""
        return LanguageModelInfo(
            name=LanguageModelName.AZURE_GPT_4o_2024_1120,
            provider=LanguageModelProvider.AZURE,
            capabilities=[ModelCapabilities.STRUCTURED_OUTPUT],
            token_limits=LanguageModelTokenLimits(
                token_limit_input=128000, token_limit_output=4096
            ),
        )

    @pytest.fixture
    def mock_language_model_info_no_structured_output(self):
        """Mock LanguageModelInfo without structured output capability."""
        return LanguageModelInfo(
            name=LanguageModelName.AZURE_GPT_35_TURBO_0125,
            provider=LanguageModelProvider.AZURE,
            capabilities=[],
            token_limits=LanguageModelTokenLimits(
                token_limit_input=16000, token_limit_output=4096
            ),
        )

    @pytest.mark.ai
    def test_web_search_config_defaults(self, mock_language_model_info) -> None:
        """
        Purpose: Verify WebSearchConfig creates with expected default values.
        Why this matters: Ensures proper default configuration for web search service.
        Setup summary: Create WebSearchConfig with language model only, assert all defaults present.
        """
        # Arrange & Act
        config = WebSearchConfig(language_model=mock_language_model_info)

        # Assert
        assert config.language_model == mock_language_model_info
        assert config.limit_token_sources == 60_000
        assert config.percentage_of_input_tokens_for_sources == 0.4
        assert config.language_model_max_input_tokens is None
        assert isinstance(config.crawler_config, BasicCrawlerConfig)
        assert config.debug is False

    @pytest.mark.ai
    def test_web_search_config_custom_values(self, mock_language_model_info) -> None:
        """
        Purpose: Verify WebSearchConfig accepts and stores custom configuration values.
        Why this matters: Ensures flexibility in configuring web search service behavior.
        Setup summary: Create WebSearchConfig with custom values for all options, assert all values stored correctly.
        """
        # Arrange
        search_engine_config = GoogleConfig(
            search_engine_name=SearchEngineType.GOOGLE,
        )

        crawler_config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC, timeout=60)

        # Act
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            limit_token_sources=50_000,
            percentage_of_input_tokens_for_sources=0.3,
            language_model_max_input_tokens=100_000,
            search_engine_config=search_engine_config,
            crawler_config=crawler_config,
            debug=True,
        )

        # Assert
        assert config.limit_token_sources == 50_000
        assert config.percentage_of_input_tokens_for_sources == 0.3
        assert config.language_model_max_input_tokens == 100_000
        assert config.search_engine_config == search_engine_config
        assert config.crawler_config == crawler_config
        assert config.debug is True

    @pytest.mark.ai
    def test_web_search_config_evaluation_check_list(
        self, mock_language_model_info
    ) -> None:
        """
        Purpose: Verify WebSearchConfig accepts and stores evaluation check list.
        Why this matters: Enables quality evaluation metrics for web search results.
        Setup summary: Create WebSearchConfig with evaluation_check_list, assert metrics stored correctly.
        """
        # Arrange
        check_list: list[EvaluationMetricName] = [
            EvaluationMetricName.HALLUCINATION,
        ]

        # Act
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            evaluation_check_list=check_list,
        )

        # Assert
        assert EvaluationMetricName.HALLUCINATION in config.evaluation_check_list

    @pytest.mark.ai
    def test_web_search_config_experimental_features(
        self, mock_language_model_info
    ) -> None:
        """
        Purpose: Verify WebSearchConfig accepts and stores experimental features configuration.
        Why this matters: Enables experimental search executor features for testing and future use.
        Setup summary: Create ExperimentalFeatures with V2 enabled, pass to WebSearchConfig, assert values stored.
        """
        # Arrange
        experimental_features = ExperimentalFeatures(
            v2_mode=WebSearchV2(enabled=True, max_steps=8)
        )

        # Act
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            experimental_features=experimental_features,
        )

        # Assert
        assert config.experimental_features.v2_mode.enabled is True
        assert config.experimental_features.v2_mode.max_steps == 8

    @pytest.mark.ai
    def test_web_search_config_query_refinement_disabled_for_no_structured_output(
        self, mock_language_model_info_no_structured_output
    ) -> None:
        """
        Purpose: Verify query refinement is automatically disabled for models without structured output.
        Why this matters: Prevents runtime errors by disabling incompatible features for unsupported models.
        Setup summary: Create WebSearchConfig with model lacking structured output, assert query refinement disabled.
        """
        # Arrange & Act
        config = WebSearchConfig(
            language_model=mock_language_model_info_no_structured_output
        )

        # Assert
        # The model_validator should disable query refinement
        assert config.query_refinement_config.enabled is False

    @pytest.mark.ai
    def test_web_search_config_query_refinement_enabled_for_structured_output(
        self, mock_language_model_info
    ) -> None:
        """
        Purpose: Verify query refinement remains enabled for models with structured output capability.
        Why this matters: Ensures query refinement works correctly with compatible language models.
        Setup summary: Create WebSearchConfig with model having structured output, assert query refinement enabled.
        """
        # Arrange & Act
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            query_refinement_config=QueryRefinementConfig(enabled=True),
        )

        # Assert
        # Should remain enabled for models with structured output capability
        assert config.query_refinement_config.enabled is True

    @pytest.mark.ai
    def test_web_search_config_percentage_validation(
        self, mock_language_model_info
    ) -> None:
        """
        Purpose: Verify percentage validation accepts valid values including boundaries.
        Why this matters: Ensures proper token allocation configuration within valid range [0.0, 1.0].
        Setup summary: Create WebSearchConfig with valid percentages (0.5, 0.0, 1.0), assert all accepted.
        """
        # Arrange & Act - Valid percentage
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            percentage_of_input_tokens_for_sources=0.5,
        )
        # Assert
        assert config.percentage_of_input_tokens_for_sources == 0.5

        # Arrange & Act - Test boundary values
        config_min = WebSearchConfig(
            language_model=mock_language_model_info,
            percentage_of_input_tokens_for_sources=0.0,
        )
        # Assert
        assert config_min.percentage_of_input_tokens_for_sources == 0.0

        config_max = WebSearchConfig(
            language_model=mock_language_model_info,
            percentage_of_input_tokens_for_sources=1.0,
        )
        # Assert
        assert config_max.percentage_of_input_tokens_for_sources == 1.0

    @pytest.mark.ai
    def test_web_search_config_invalid_percentage(
        self, mock_language_model_info
    ) -> None:
        """
        Purpose: Verify invalid percentage values raise ValidationError.
        Why this matters: Prevents misconfiguration that could cause runtime errors or unexpected behavior.
        Setup summary: Attempt to create WebSearchConfig with invalid percentages (-0.1, 1.1), assert ValidationError raised.
        """
        # Arrange & Act & Assert - Test negative percentage
        with pytest.raises(ValidationError):
            WebSearchConfig(
                language_model=mock_language_model_info,
                percentage_of_input_tokens_for_sources=-0.1,
            )

        # Arrange & Act & Assert - Test percentage > 1.0
        with pytest.raises(ValidationError):
            WebSearchConfig(
                language_model=mock_language_model_info,
                percentage_of_input_tokens_for_sources=1.1,
            )

    @pytest.mark.ai
    def test_web_search_config_tool_descriptions(
        self, mock_language_model_info
    ) -> None:
        """
        Purpose: Verify WebSearchConfig accepts and stores custom tool descriptions.
        Why this matters: Enables customization of tool descriptions for different use cases.
        Setup summary: Create WebSearchConfig with custom tool descriptions, assert values stored correctly.
        """
        # Arrange
        tool_desc: str = "Custom tool description"
        system_desc: str = "Custom system prompt description"

        # Act
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            tool_description=tool_desc,
            tool_description_for_system_prompt=system_desc,
        )

        # Assert
        assert config.tool_description == "Custom tool description"
        assert (
            config.tool_description_for_system_prompt
            == "Custom system prompt description"
        )

    @pytest.mark.ai
    def test_web_search_config_serialization(self, mock_language_model_info) -> None:
        """
        Purpose: Verify WebSearchConfig serializes correctly to dictionary format.
        Why this matters: Ensures proper data serialization for configuration storage and API responses.
        Setup summary: Create WebSearchConfig, call model_dump(), assert dictionary contains all key fields.
        """
        # Arrange & Act
        config = WebSearchConfig(language_model=mock_language_model_info, debug=True)

        config_dict = config.model_dump()

        # Assert
        assert "language_model" in config_dict
        assert "search_engine_config" in config_dict
        assert "crawler_config" in config_dict
        assert "experimental_features" in config_dict
        assert config_dict["debug"] is True

    @pytest.mark.ai
    def test_web_search_config_with_all_features(
        self, mock_language_model_info
    ) -> None:
        """
        Purpose: Verify WebSearchConfig creates correctly with all optional features configured.
        Why this matters: Ensures comprehensive configuration testing and validates all feature integrations.
        Setup summary: Create WebSearchConfig with all features enabled and customized, assert all values stored correctly.
        """
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            limit_token_sources=80_000,
            percentage_of_input_tokens_for_sources=0.35,
            language_model_max_input_tokens=120_000,
            search_engine_config=GoogleConfig(
                search_engine_name=SearchEngineType.GOOGLE,
            ),
            crawler_config=BasicCrawlerConfig(
                crawler_type=CrawlerType.BASIC,
                timeout=45,
            ),
            evaluation_check_list=[EvaluationMetricName.HALLUCINATION],
            query_refinement_config=QueryRefinementConfig(
                enabled=True, system_prompt="Custom refinement prompt"
            ),
            tool_parameters_config=WebSearchToolParametersConfig(
                query_description="Custom query description",
                date_restrict_description="Custom date description",
            ),
            experimental_features=ExperimentalFeatures(
                v1_mode=WebSearchV1(
                    refine_query_mode=RefineQueryMode.ADVANCED, max_queries=7
                ),
                v2_mode=WebSearchV2(enabled=True, max_steps=6),
            ),
            debug=True,
        )

        # Verify all configurations are set correctly
        assert config.limit_token_sources == 80_000
        assert config.percentage_of_input_tokens_for_sources == 0.35
        assert config.language_model_max_input_tokens == 120_000
        assert config.search_engine_config.search_engine_name == SearchEngineType.GOOGLE
        assert config.crawler_config.crawler_type == CrawlerType.BASIC
        assert config.crawler_config.timeout == 45
        assert EvaluationMetricName.HALLUCINATION in config.evaluation_check_list
        assert config.query_refinement_config.enabled is True
        assert config.experimental_features.v1_mode.max_queries == 7
        assert config.experimental_features.v2_mode.enabled is True
        assert config.experimental_features.v2_mode.max_steps == 6
        assert config.debug is True
