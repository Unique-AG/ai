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

    def test_answer_generation_config_defaults(self):
        """Test AnswerGenerationConfig with default values."""
        config = AnswerGenerationConfig()

        assert config.limit_token_sources == 10000
        assert config.max_chunks_to_consider == 20
        assert config.number_history_interactions_included == 2

    def test_answer_generation_config_custom_values(self):
        """Test AnswerGenerationConfig with custom values."""
        config = AnswerGenerationConfig(
            limit_token_sources=15000,
            max_chunks_to_consider=30,
            number_history_interactions_included=5,
        )

        assert config.limit_token_sources == 15000
        assert config.max_chunks_to_consider == 30
        assert config.number_history_interactions_included == 5


class TestWebSearchV1:
    """Test cases for WebSearchV1 configuration."""

    def test_web_search_v1_defaults(self):
        """Test WebSearchV1 with default values."""
        config = WebSearchV1()

        assert config.refine_query_mode == RefineQueryMode.BASIC
        assert config.max_queries == 5

    def test_web_search_v1_custom_values(self):
        """Test WebSearchV1 with custom values."""
        config = WebSearchV1(refine_query_mode=RefineQueryMode.ADVANCED, max_queries=10)

        assert config.refine_query_mode == RefineQueryMode.ADVANCED
        assert config.max_queries == 10


class TestWebSearchV2:
    """Test cases for WebSearchV2 configuration."""

    def test_web_search_v2_enabled(self):
        """Test WebSearchV2 when enabled."""
        config = WebSearchV2(
            enabled=True, max_steps=10, tool_description="Custom V2 description"
        )

        assert config.enabled is True
        assert config.max_steps == 10
        assert config.tool_description == "Custom V2 description"

    def test_web_search_v2_tool_descriptions(self):
        """Test WebSearchV2 tool descriptions."""
        config = WebSearchV2(
            tool_description="Custom tool description",
            tool_description_for_system_prompt="Custom system prompt description",
        )

        assert config.tool_description == "Custom tool description"
        assert (
            config.tool_description_for_system_prompt
            == "Custom system prompt description"
        )


class TestExperimentalFeatures:
    """Test cases for ExperimentalFeatures configuration."""

    def test_experimental_features_defaults(self):
        """Test ExperimentalFeatures with default values."""
        config = ExperimentalFeatures()

        assert isinstance(config.v1_mode, WebSearchV1)
        assert isinstance(config.v2_mode, WebSearchV2)
        assert config.v2_mode.enabled is False

    def test_experimental_features_custom_v1(self):
        """Test ExperimentalFeatures with custom V1 configuration."""
        v1_config = WebSearchV1(
            refine_query_mode=RefineQueryMode.ADVANCED, max_queries=8
        )

        config = ExperimentalFeatures(v1_mode=v1_config)

        assert config.v1_mode.refine_query_mode == RefineQueryMode.ADVANCED
        assert config.v1_mode.max_queries == 8

    def test_experimental_features_custom_v2(self):
        """Test ExperimentalFeatures with custom V2 configuration."""
        v2_config = WebSearchV2(enabled=True, max_steps=7)

        config = ExperimentalFeatures(v2_mode=v2_config)

        assert config.v2_mode.enabled is True
        assert config.v2_mode.max_steps == 7


class TestQueryRefinementConfig:
    """Test cases for QueryRefinementConfig."""

    def test_query_refinement_config_defaults(self):
        """Test QueryRefinementConfig with default values."""
        config = QueryRefinementConfig()

        assert config.enabled is True
        assert len(config.system_prompt) > 0

    def test_query_refinement_config_disabled(self):
        """Test QueryRefinementConfig when disabled."""
        config = QueryRefinementConfig(
            enabled=False, system_prompt="Custom system prompt"
        )

        assert config.enabled is False
        assert config.system_prompt == "Custom system prompt"


class TestWebSearchToolParametersConfig:
    """Test cases for WebSearchToolParametersConfig."""

    def test_tool_parameters_config_defaults(self):
        """Test WebSearchToolParametersConfig with default values."""
        config = WebSearchToolParametersConfig()

        assert "search query" in config.query_description.lower()
        assert len(config.date_restrict_description) > 0

    def test_tool_parameters_config_custom(self):
        """Test WebSearchToolParametersConfig with custom values."""
        config = WebSearchToolParametersConfig(
            query_description="Custom query description",
            date_restrict_description="Custom date restriction description",
        )

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

    def test_web_search_config_defaults(self, mock_language_model_info):
        """Test WebSearchConfig with default values."""
        config = WebSearchConfig(language_model=mock_language_model_info)

        assert config.language_model == mock_language_model_info
        assert config.limit_token_sources == 60_000
        assert config.percentage_of_input_tokens_for_sources == 0.4
        assert config.language_model_max_input_tokens is None
        assert isinstance(config.crawler_config, BasicCrawlerConfig)
        assert config.debug is False

    def test_web_search_config_custom_values(self, mock_language_model_info):
        """Test WebSearchConfig with custom values."""
        search_engine_config = GoogleConfig(
            search_engine_name=SearchEngineType.GOOGLE,
        )

        crawler_config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC, timeout=60)

        config = WebSearchConfig(
            language_model=mock_language_model_info,
            limit_token_sources=50_000,
            percentage_of_input_tokens_for_sources=0.3,
            language_model_max_input_tokens=100_000,
            search_engine_config=search_engine_config,
            crawler_config=crawler_config,
            debug=True,
        )

        assert config.limit_token_sources == 50_000
        assert config.percentage_of_input_tokens_for_sources == 0.3
        assert config.language_model_max_input_tokens == 100_000
        assert config.search_engine_config == search_engine_config
        assert config.crawler_config == crawler_config
        assert config.debug is True

    def test_web_search_config_evaluation_check_list(self, mock_language_model_info):
        """Test WebSearchConfig evaluation check list."""
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            evaluation_check_list=[
                EvaluationMetricName.HALLUCINATION,
            ],
        )

        assert EvaluationMetricName.HALLUCINATION in config.evaluation_check_list

    def test_web_search_config_experimental_features(self, mock_language_model_info):
        """Test WebSearchConfig with experimental features."""
        experimental_features = ExperimentalFeatures(
            v2_mode=WebSearchV2(enabled=True, max_steps=8)
        )

        config = WebSearchConfig(
            language_model=mock_language_model_info,
            experimental_features=experimental_features,
        )

        assert config.experimental_features.v2_mode.enabled is True
        assert config.experimental_features.v2_mode.max_steps == 8

    def test_web_search_config_query_refinement_disabled_for_no_structured_output(
        self, mock_language_model_info_no_structured_output
    ):
        """Test that query refinement is disabled for models without structured output."""
        config = WebSearchConfig(
            language_model=mock_language_model_info_no_structured_output
        )

        # The model_validator should disable query refinement
        assert config.query_refinement_config.enabled is False

    def test_web_search_config_query_refinement_enabled_for_structured_output(
        self, mock_language_model_info
    ):
        """Test that query refinement remains enabled for models with structured output."""
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            query_refinement_config=QueryRefinementConfig(enabled=True),
        )

        # Should remain enabled for models with structured output capability
        assert config.query_refinement_config.enabled is True

    def test_web_search_config_percentage_validation(self, mock_language_model_info):
        """Test percentage validation for input tokens."""
        # Valid percentage
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            percentage_of_input_tokens_for_sources=0.5,
        )
        assert config.percentage_of_input_tokens_for_sources == 0.5

        # Test boundary values
        config_min = WebSearchConfig(
            language_model=mock_language_model_info,
            percentage_of_input_tokens_for_sources=0.0,
        )
        assert config_min.percentage_of_input_tokens_for_sources == 0.0

        config_max = WebSearchConfig(
            language_model=mock_language_model_info,
            percentage_of_input_tokens_for_sources=1.0,
        )
        assert config_max.percentage_of_input_tokens_for_sources == 1.0

    def test_web_search_config_invalid_percentage(self, mock_language_model_info):
        """Test that invalid percentages raise validation errors."""
        # Test negative percentage
        with pytest.raises(ValidationError):
            WebSearchConfig(
                language_model=mock_language_model_info,
                percentage_of_input_tokens_for_sources=-0.1,
            )

        # Test percentage > 1.0
        with pytest.raises(ValidationError):
            WebSearchConfig(
                language_model=mock_language_model_info,
                percentage_of_input_tokens_for_sources=1.1,
            )

    def test_web_search_config_tool_descriptions(self, mock_language_model_info):
        """Test WebSearchConfig tool descriptions."""
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            tool_description="Custom tool description",
            tool_description_for_system_prompt="Custom system prompt description",
        )

        assert config.tool_description == "Custom tool description"
        assert (
            config.tool_description_for_system_prompt
            == "Custom system prompt description"
        )

    def test_web_search_config_serialization(self, mock_language_model_info):
        """Test WebSearchConfig serialization."""
        config = WebSearchConfig(language_model=mock_language_model_info, debug=True)

        config_dict = config.model_dump()

        assert "language_model" in config_dict
        assert "search_engine_config" in config_dict
        assert "crawler_config" in config_dict
        assert "experimental_features" in config_dict
        assert config_dict["debug"] is True

    def test_web_search_config_with_all_features(self, mock_language_model_info):
        """Test WebSearchConfig with all features configured."""
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
