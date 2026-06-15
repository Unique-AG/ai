import pytest
from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_stock_ticker.config import StockTickerConfig
from unique_toolkit.agentic.tools.experimental.open_file_tool.config import (
    OpenFileToolConfig,
)
from unique_toolkit.agentic.tools.experimental.todo import (
    TodoConfig,
    TodoWriteTool,
)
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterExtendedConfig,
)
from unique_toolkit.agentic.tools.tool import ToolBuildConfig
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
    ModelCapabilities,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenLimits
from unique_user_memory.config import UserMemoryConfig

from unique_orchestrator.config import (
    EvaluationConfig,
    UniqueAIConfig,
    UniqueAIServices,
    UniqueAISpaceConfig,
)


class TestUniqueAISpaceConfigModelSwitching:
    def test_accepts_camel_case_model_switching_fields(self):
        config = UniqueAISpaceConfig.model_validate(
            {
                "allowModelSwitching": True,
                "switchableLanguageModels": [
                    {
                        "displayName": "GPT-4o",
                        "languageModel": LanguageModelName.AZURE_GPT_4o_2024_1120,
                    }
                ],
            }
        )

        assert config.allow_model_switching is True
        assert len(config.switchable_language_models) == 1
        assert config.switchable_language_models[0].display_name == "GPT-4o"
        assert (
            config.switchable_language_models[0].language_model.name
            == LanguageModelName.AZURE_GPT_4o_2024_1120
        )

    @pytest.mark.ai
    def test_defaults_absent_switchable_language_models_from_node_backend(self):
        """Purpose: Verify omitted node-backend model-switching payloads parse.
        Why this matters: Existing spaces can omit the new JSON field before it is configured.
        Setup summary: Validate a payload without switchableLanguageModels and assert it defaults to [].
        """
        config = UniqueAIConfig.model_validate(
            {
                "space": {
                    "allowModelSwitching": False,
                },
            }
        )

        assert config.space.switchable_language_models == []


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
    configuration=CodeInterpreterExtendedConfig(),
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


class TestUniqueAIConfigOpenFileValidator:
    def test_requires_responses_api_when_open_file_tool_is_enabled(self):
        with pytest.raises(
            ValueError,
            match="open_file_tool_config.enabled requires the Responses API",
        ):
            UniqueAIConfig(
                agent={
                    "experimental": {
                        "open_file_tool_config": OpenFileToolConfig(enabled=True)
                    }
                }
            )

    def test_allows_open_file_tool_when_responses_api_is_enabled(self):
        config = UniqueAIConfig(
            agent={
                "experimental": {
                    "responses_api_config": {"use_responses_api": True},
                    "open_file_tool_config": OpenFileToolConfig(enabled=True),
                }
            }
        )

        assert config.agent.experimental.open_file_tool_config.enabled is True
        assert config.agent.experimental.responses_api_config.use_responses_api is True

    def test_does_not_enable_responses_api_when_model_does_not_support_it(self):
        """Code Interpreter in space.tools must not enable Responses API if the model
        does not advertise ModelCapabilities.RESPONSES_API — the tool would be unusable
        and silently upgrading the API would cause a different failure."""
        config = _make_config(
            tools=[CODE_INTERPRETER_TOOL], supports_responses_api=False
        )

        assert config.agent.experimental.responses_api_config.use_responses_api is False

    def test_does_not_change_config_when_code_interpreter_not_in_tools(self):
        """When Code Interpreter is not selected at all, the validator must be a no-op."""
        config = _make_config(tools=[], supports_responses_api=True)

        assert config.agent.experimental.responses_api_config.use_responses_api is False

    def test_does_not_override_already_enabled_responses_api(self):
        """When use_responses_api is already True, the validator must not change it."""
        from unique_orchestrator.config import ExperimentalConfig, ResponsesApiConfig

        config = UniqueAIConfig(
            space=UniqueAISpaceConfig(
                language_model=_make_model(supports_responses_api=True),
                tools=[CODE_INTERPRETER_TOOL],
            ),
            agent={
                "experimental": ExperimentalConfig(
                    responses_api_config=ResponsesApiConfig(
                        use_responses_api=True,
                    )
                )
            },
        )

        assert config.agent.experimental.responses_api_config.use_responses_api is True


class TestUniqueAIConfigGpt55ResponsesApiValidator:
    """Test suite for UniqueAIConfig.enable_responses_api_for_gpt_55_and_gpt_55_pro validator.

    GPT-5.5 (AZURE_GPT_55_2026_0424) and GPT-5.5-Pro (AZURE_GPT_55_PRO_2026_0424)
    reject requests that combine `tools` with `reasoning_effort` on
    /v1/chat/completions and demand /v1/responses. The validator forces the
    Responses API on when either of these models is selected, regardless of
    which tools are configured.
    Tracked in Jira: UN-20123.
    """

    @pytest.mark.parametrize(
        "model_name",
        [
            LanguageModelName.AZURE_GPT_55_2026_0424,
            LanguageModelName.AZURE_GPT_55_PRO_2026_0424,
        ],
    )
    def test_enables_responses_api_for_affected_models(
        self, model_name: LanguageModelName
    ):
        """When the selected model is GPT-5.5 or GPT-5.5-Pro, the validator must
        auto-enable use_responses_api so the runner routes to /v1/responses."""
        model = LanguageModelInfo.from_name(model_name)

        config = UniqueAIConfig(
            space=UniqueAISpaceConfig(language_model=model, tools=[]),
        )

        assert config.agent.experimental.responses_api_config.use_responses_api is True

    @pytest.mark.parametrize(
        "model_name",
        [
            LanguageModelName.AZURE_GPT_55_2026_0424,
            LanguageModelName.AZURE_GPT_55_PRO_2026_0424,
        ],
    )
    def test_enables_responses_api_for_affected_models_with_tools(
        self, model_name: LanguageModelName
    ):
        """The auto-enable must apply even when tools other than Code Interpreter
        are configured — the GPT-5.5(-Pro) transport requirement is independent
        of the Code Interpreter validator above."""
        model = LanguageModelInfo.from_name(model_name)

        config = UniqueAIConfig(
            space=UniqueAISpaceConfig(
                language_model=model,
                tools=[CODE_INTERPRETER_TOOL],
            ),
        )

        assert config.agent.experimental.responses_api_config.use_responses_api is True

    def test_does_not_enable_responses_api_for_other_models(self):
        """When the selected model is neither GPT-5.5 nor GPT-5.5-Pro, the
        validator must be a no-op even if the model supports the Responses API.
        Otherwise the TEMP FIX could mask real configuration issues for
        unaffected models."""
        config = _make_config(tools=[], supports_responses_api=True)

        assert config.agent.experimental.responses_api_config.use_responses_api is False

    @pytest.mark.parametrize(
        "model_name",
        [
            LanguageModelName.AZURE_GPT_55_2026_0424,
            LanguageModelName.AZURE_GPT_55_PRO_2026_0424,
        ],
    )
    def test_keeps_responses_api_enabled_when_already_enabled(
        self, model_name: LanguageModelName
    ):
        """When use_responses_api is already True for an affected model, the
        validator must leave it True (i.e. it is idempotent for those models)."""
        from unique_orchestrator.config import ExperimentalConfig, ResponsesApiConfig

        model = LanguageModelInfo.from_name(model_name)

        config = UniqueAIConfig(
            space=UniqueAISpaceConfig(language_model=model, tools=[]),
            agent={
                "experimental": ExperimentalConfig(
                    responses_api_config=ResponsesApiConfig(use_responses_api=True),
                )
            },
        )

        assert config.agent.experimental.responses_api_config.use_responses_api is True


class TestUniqueAIConfigInjectTodoToolValidator:
    """Test suite for UniqueAIConfig.inject_todo_tool validator.

    The validator bridges the experimental ``todo_config`` flag with the
    declarative ``space.tools`` list that ``ToolManager`` iterates over.
    Without it, toggling ``todo_config.enabled = True`` is a no-op because
    ``ToolManager._init__tools`` only builds tools listed in
    ``config.space.tools``.

    Mirrors the established ``inject_retrieve_search_scope_tool`` precedent.
    """

    def _todo_entries(self, config: UniqueAIConfig) -> list[ToolBuildConfig]:
        return [t for t in config.space.tools if t.name == TodoWriteTool.name]

    def test_appends_todo_tool_when_enabled(self):
        """When ``todo_config.enabled=True`` and TodoWrite is not in
        ``space.tools``, the validator must append a ``ToolBuildConfig``
        entry carrying the same ``TodoConfig`` so the factory can build it."""
        config = UniqueAIConfig(
            space=UniqueAISpaceConfig(
                language_model=_make_model(supports_responses_api=True),
                tools=[],
            ),
            agent={"experimental": {"todo_config": TodoConfig(enabled=True)}},
        )

        entries = self._todo_entries(config)
        assert len(entries) == 1
        assert entries[0].name == TodoWriteTool.name
        assert isinstance(entries[0].configuration, TodoConfig)
        assert entries[0].configuration.enabled is True
        assert entries[0].display_name == TodoConfig().display_name

    def test_removes_todo_tool_when_disabled(self):
        """When ``todo_config.enabled=False`` but TodoWrite is already in
        ``space.tools`` (e.g. inherited from a previous run), the validator
        must strip it so the LLM never sees the description."""
        config = UniqueAIConfig(
            space=UniqueAISpaceConfig(
                language_model=_make_model(supports_responses_api=True),
                tools=[
                    ToolBuildConfig(
                        name=TodoWriteTool.name,
                        configuration=TodoConfig(enabled=False),
                    )
                ],
            ),
            agent={"experimental": {"todo_config": TodoConfig(enabled=False)}},
        )

        assert self._todo_entries(config) == []

    def test_does_not_duplicate_when_already_present(self):
        """When ``todo_config.enabled=True`` and TodoWrite is already in
        ``space.tools``, the validator must be idempotent — no second entry
        is appended (which would surface duplicate tool definitions to the
        model)."""
        existing = ToolBuildConfig(
            name=TodoWriteTool.name,
            configuration=TodoConfig(enabled=True),
        )
        config = UniqueAIConfig(
            space=UniqueAISpaceConfig(
                language_model=_make_model(supports_responses_api=True),
                tools=[existing],
            ),
            agent={"experimental": {"todo_config": TodoConfig(enabled=True)}},
        )

        assert len(self._todo_entries(config)) == 1

    def test_no_op_when_disabled_and_not_present(self):
        """When ``todo_config.enabled=False`` and TodoWrite is not in
        ``space.tools``, the validator must leave ``space.tools`` untouched
        so existing defaults (InternalSearch, WebSearch, …) are preserved."""
        default_tools = UniqueAISpaceConfig(
            language_model=_make_model(supports_responses_api=True)
        ).tools
        config = _make_config(tools=default_tools)

        assert self._todo_entries(config) == []
        assert [t.name for t in config.space.tools] == [t.name for t in default_tools]


class TestUniqueAIConfigUserMemory:
    def test_user_memory_config_defaults_to_disabled(self):
        config = UniqueAIConfig()

        assert isinstance(
            config.agent.experimental.user_memory_config, UserMemoryConfig
        )
        assert config.agent.experimental.user_memory_config.enabled is False

    def test_user_memory_config_parses_enabled_payload(self):
        config = UniqueAIConfig(
            agent={
                "experimental": {
                    "user_memory_config": {
                        "enabled": True,
                        "max_tokens": 1500,
                    }
                }
            }
        )

        memory_config = config.agent.experimental.user_memory_config
        assert memory_config.enabled is True
        assert memory_config.max_tokens == 1500
