from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_stock_ticker.config import StockTickerConfig
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.manager import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.tool import ToolBuildConfig
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelProvider,
    ModelCapabilities,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenLimits

from unique_orchestrator.config import (
    CodeInterpreterExtendedConfig,
    EvaluationConfig,
    UniqueAIConfig,
    UniqueAIServices,
    UniqueAISpaceConfig,
)


class TestUniqueAIServicesStockTickerConfigValidator:
    """Test suite for UniqueAIServices.check_if_stock_ticker_config_is_none validator"""

    def test_returns_default_config_when_none(self):
        """Test that a default StockTickerConfig with enabled=False is returned when config is None"""
        services = UniqueAIServices(stock_ticker_config=None)

        assert isinstance(services.stock_ticker_config, StockTickerConfig)
        assert services.stock_ticker_config.enabled is False

    def test_returns_default_config_when_empty_dict(self):
        """Test that a default StockTickerConfig with enabled=False is returned when config is empty dict"""
        services = UniqueAIServices(stock_ticker_config={})

        assert isinstance(services.stock_ticker_config, StockTickerConfig)
        assert services.stock_ticker_config.enabled is False

    def test_returns_provided_config_when_valid(self):
        """Test that the provided config is returned when it's a valid StockTickerConfig"""
        custom_config = StockTickerConfig(enabled=True)
        services = UniqueAIServices(stock_ticker_config=custom_config)

        assert services.stock_ticker_config.enabled is True

    def test_returns_provided_dict_config_when_valid(self):
        """Test that the provided dict config is used when it contains valid data"""
        services = UniqueAIServices(stock_ticker_config={"enabled": True})

        assert services.stock_ticker_config.enabled is True


class TestUniqueAIServicesFollowUpQuestionsConfigValidator:
    """Test suite for UniqueAIServices.check_if_follow_up_questions_config_is_none validator"""

    def test_returns_default_config_when_none(self):
        """Test that a default FollowUpQuestionsConfig with number_of_questions=0 is returned when config is None"""
        services = UniqueAIServices(follow_up_questions_config=None)

        assert isinstance(services.follow_up_questions_config, FollowUpQuestionsConfig)
        assert services.follow_up_questions_config.number_of_questions == 0

    def test_returns_default_config_when_empty_dict(self):
        """Test that a default FollowUpQuestionsConfig with number_of_questions=0 is returned when config is empty dict"""
        services = UniqueAIServices(follow_up_questions_config={})

        assert isinstance(services.follow_up_questions_config, FollowUpQuestionsConfig)
        assert services.follow_up_questions_config.number_of_questions == 0

    def test_returns_provided_config_when_valid(self):
        """Test that the provided config is returned when it's a valid FollowUpQuestionsConfig"""
        custom_config = FollowUpQuestionsConfig(number_of_questions=5)
        services = UniqueAIServices(follow_up_questions_config=custom_config)

        assert services.follow_up_questions_config.number_of_questions == 5

    def test_returns_provided_dict_config_when_valid(self):
        """Test that the provided dict config is used when it contains valid data"""
        services = UniqueAIServices(
            follow_up_questions_config={"number_of_questions": 7}
        )

        assert services.follow_up_questions_config.number_of_questions == 7


class TestUniqueAIServicesEvaluationConfigValidator:
    """Test suite for UniqueAIServices.check_if_evaluation_config_is_none validator"""

    def test_returns_default_config_when_none(self):
        """Test that a default EvaluationConfig is returned when config is None"""
        services = UniqueAIServices(evaluation_config=None)

        assert isinstance(services.evaluation_config, EvaluationConfig)

    def test_returns_default_config_when_empty_dict(self):
        """Test that a default EvaluationConfig is returned when config is empty dict"""
        services = UniqueAIServices(evaluation_config={})

        assert isinstance(services.evaluation_config, EvaluationConfig)

    def test_returns_provided_config_when_valid(self):
        """Test that the provided config is returned when it's a valid EvaluationConfig"""
        custom_config = EvaluationConfig()
        services = UniqueAIServices(evaluation_config=custom_config)

        assert isinstance(services.evaluation_config, EvaluationConfig)

    def test_returns_provided_dict_config_when_valid(self):
        """Test that the provided dict config is used when it contains valid data"""
        services = UniqueAIServices(evaluation_config={"hallucination_config": {}})

        assert isinstance(services.evaluation_config, EvaluationConfig)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(*, supports_responses_api: bool) -> LanguageModelInfo:
    capabilities = [ModelCapabilities.FUNCTION_CALLING, ModelCapabilities.STREAMING]
    if supports_responses_api:
        capabilities.append(ModelCapabilities.RESPONSES_API)
    return LanguageModelInfo(
        name="test-model",
        provider=LanguageModelProvider.AZURE,
        version="test",
        capabilities=capabilities,
        token_limits=LanguageModelTokenLimits(
            token_limit_input=10_000, token_limit_output=2_000
        ),
    )


def _make_config(
    *,
    tools: list[ToolBuildConfig],
    supports_responses_api: bool = True,
) -> UniqueAIConfig:
    return UniqueAIConfig(
        space=UniqueAISpaceConfig(
            language_model=_make_model(supports_responses_api=supports_responses_api),
            tools=tools,
        )
    )


CODE_INTERPRETER_TOOL = ToolBuildConfig(
    name=OpenAIBuiltInToolName.CODE_INTERPRETER,
    configuration=OpenAICodeInterpreterConfig(),
)


class TestUniqueAIConfigCodeInterpreterValidator:
    """Test suite for UniqueAIConfig.enable_responses_api_for_code_interpreter_tool validator.

    The validator must bridge the gap between the old "advanced experimental settings" path
    (where the admin explicitly set `responses_api_config.use_responses_api = True` and
    `responses_api_config.code_interpreter = ...`) and the new "direct tool selection" path
    (where the admin picks Code Interpreter from the regular tools list in the UI).

    Without the validator the new path leaves `use_responses_api = False`, which causes
    `build_unique_ai` to route to `_build_completions` instead of `_build_responses`, and
    leaves `responses_api_config.code_interpreter = None`, which skips all postprocessors
    for generated-file display and executed-code display.
    """

    def test_enables_responses_api_when_code_interpreter_tool_added_directly(self):
        """When CODE_INTERPRETER is in space.tools and model supports Responses API,
        use_responses_api must be set to True so the builder routes to _build_responses."""
        config = _make_config(
            tools=[CODE_INTERPRETER_TOOL], supports_responses_api=True
        )

        assert config.agent.experimental.responses_api_config.use_responses_api is True

    def test_populates_code_interpreter_config_with_defaults_when_not_set(self):
        """When CODE_INTERPRETER is added directly as a tool and no advanced code_interpreter
        config was provided, a default CodeInterpreterExtendedConfig must be created so that
        _build_responses registers the postprocessors for file and code display."""
        config = _make_config(
            tools=[CODE_INTERPRETER_TOOL], supports_responses_api=True
        )

        assert isinstance(
            config.agent.experimental.responses_api_config.code_interpreter,
            CodeInterpreterExtendedConfig,
        )

    def test_does_not_enable_responses_api_when_model_does_not_support_it(self):
        """Code Interpreter in space.tools must not enable Responses API if the model
        does not advertise ModelCapabilities.RESPONSES_API — the tool would be unusable
        and silently upgrading the API would cause a different failure."""
        config = _make_config(
            tools=[CODE_INTERPRETER_TOOL], supports_responses_api=False
        )

        assert config.agent.experimental.responses_api_config.use_responses_api is False
        assert config.agent.experimental.responses_api_config.code_interpreter is None

    def test_does_not_change_config_when_code_interpreter_not_in_tools(self):
        """When Code Interpreter is not selected at all, the validator must be a no-op."""
        config = _make_config(tools=[], supports_responses_api=True)

        assert config.agent.experimental.responses_api_config.use_responses_api is False
        assert config.agent.experimental.responses_api_config.code_interpreter is None

    def test_preserves_explicit_code_interpreter_config_when_already_set(self):
        """When an admin also provided a custom CodeInterpreterExtendedConfig via the advanced
        settings, the validator must not overwrite it — the explicit config wins."""
        from unique_orchestrator.config import ExperimentalConfig, ResponsesApiConfig

        custom_ci_config = CodeInterpreterExtendedConfig(
            executed_code_display_config=None,
        )
        config = UniqueAIConfig(
            space=UniqueAISpaceConfig(
                language_model=_make_model(supports_responses_api=True),
                tools=[CODE_INTERPRETER_TOOL],
            ),
            agent={
                "experimental": ExperimentalConfig(
                    responses_api_config=ResponsesApiConfig(
                        use_responses_api=True,
                        code_interpreter=custom_ci_config,
                    )
                )
            },
        )

        assert (
            config.agent.experimental.responses_api_config.code_interpreter
            is custom_ci_config
        )
