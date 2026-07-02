from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.service import InternalSearchTool
from unique_toolkit.agentic.tools.experimental.open_file_tool.config import (
    OpenFileToolConfig,
)
from unique_toolkit.agentic.tools.experimental.retrieve_search_scope_tool import (
    RetrieveSearchScopeTool,
)
from unique_toolkit.agentic.tools.experimental.retrieve_search_scope_tool.config import (
    RetrieveSearchScopeConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterExtendedConfig,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import ToolBuildConfig
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelProvider,
    ModelCapabilities,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenLimits
from unique_web_search.config import WebSearchConfig
from unique_web_search.service import WebSearchTool

from unique_orchestrator.config import UniqueAIConfig, UniqueAISpaceConfig
from unique_orchestrator.unique_ai_builder import (
    _apply_model_choice_override,
    _record_language_model_debug_info,
)


def _make_event(
    model_choice: LanguageModelInfo,
    *,
    has_model_choice_override: bool,
) -> MagicMock:
    event = MagicMock()
    event.company_id = "company_1"
    event.payload.model_choice = model_choice
    event.payload.has_model_choice_override = has_model_choice_override
    return event


def _make_model(
    name: str,
    capabilities: list[ModelCapabilities] | None = None,
) -> LanguageModelInfo:
    return LanguageModelInfo(
        name=name,
        provider=LanguageModelProvider.AZURE,
        version="test",
        capabilities=capabilities
        or [
            ModelCapabilities.CHAT_COMPLETIONS_API,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.STREAMING,
        ],
        token_limits=LanguageModelTokenLimits(
            token_limit_input=10_000,
            token_limit_output=2_000,
        ),
    )


@pytest.mark.ai
def test_space_config_accepts_allow_model_switching_alias() -> None:
    """
    Purpose: Verify backend camelCase config populates the Python space config flag.
    Why this matters: The node backend forwards allowModelSwitching into the event payload.
    Setup summary: Validate camelCase input; assert the snake_case field is enabled.
    """
    config = UniqueAISpaceConfig.model_validate(
        {
            "allowModelSwitching": True,
            "tools": [],
        }
    )

    assert config.allow_model_switching is True


@pytest.mark.ai
def test_model_choice_keeps_default_model_when_choice_was_not_sent() -> None:
    """
    Purpose: Verify an omitted model_choice does not override the configured model.
    Why this matters: The payload field is defaulted, so field presence is the absence signal.
    Setup summary: Simulate no modelChoice field; assert the default remains.
    """
    default_model = _make_model("default-model")
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            language_model=default_model,
            tools=[],
        )
    )

    config = _apply_model_choice_override(
        event=_make_event(selected_model, has_model_choice_override=False),
        logger=MagicMock(),
        config=config,
    )

    assert config.space.language_model is default_model


@pytest.mark.ai
def test_model_choice_keeps_default_model_when_selection_is_disabled() -> None:
    """
    Purpose: Verify model_choice is ignored when user model selection is disabled.
    Why this matters: Backend config must explicitly allow per-message model overrides.
    Setup summary: Provide a selected model with the override flag off; assert the default remains.
    """
    default_model = _make_model("default-model")
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=False,
            language_model=default_model,
            tools=[],
        )
    )

    config = _apply_model_choice_override(
        event=_make_event(selected_model, has_model_choice_override=True),
        logger=MagicMock(),
        config=config,
    )

    assert config.space.language_model is default_model


@pytest.mark.ai
def test_model_choice_uses_selected_model_when_selection_is_enabled() -> None:
    """
    Purpose: Verify model_choice overrides the configured model.
    Why this matters: The event payload already carries the resolved LanguageModelInfo.
    Setup summary: Provide a selected model; assert the selected model becomes active.
    """
    default_model = _make_model("default-model")
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            language_model=default_model,
            tools=[],
        )
    )

    config = _apply_model_choice_override(
        event=_make_event(selected_model, has_model_choice_override=True),
        logger=MagicMock(),
        config=config,
    )

    assert config.space.language_model == selected_model


@pytest.mark.ai
def test_record_language_model_debug_info_uses_effective_model() -> None:
    """
    Purpose: Verify debug info records the active language model.
    Why this matters: Support needs to see the exact model used after any override.
    Setup summary: Build a config with a selected model; assert the serialized model is added.
    """
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            language_model=selected_model,
            tools=[],
        )
    )
    debug_info_manager = MagicMock()

    _record_language_model_debug_info(
        debug_info_manager=debug_info_manager,
        config=config,
    )

    debug_info_manager.add.assert_called_once_with(
        "language_model",
        {
            "name": "selected-model",
            "provider": "AZURE",
            "family": "unknown",
        },
    )


@pytest.mark.ai
def test_model_choice_uses_selected_model_when_present_in_allowlist() -> None:
    """
    Purpose: Verify switchable_language_models permits listed per-message model choices.
    Why this matters: Space admins need a bounded model picker without blocking valid selections.
    Setup summary: Configure an allowlist containing the selected model; assert the override applies.
    """
    default_model = _make_model("default-model")
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            switchable_language_models=[
                {
                    "displayName": "Selected Model",
                    "languageModel": _make_model("selected-model"),
                }
            ],
            language_model=default_model,
            tools=[],
        )
    )

    config = _apply_model_choice_override(
        event=_make_event(selected_model, has_model_choice_override=True),
        logger=MagicMock(),
        config=config,
    )

    assert config.space.language_model == selected_model


@pytest.mark.ai
def test_model_choice_rejects_selected_model_when_allowlist_entry_differs() -> None:
    """
    Purpose: Verify switchable_language_models requires the full LanguageModelInfo to match.
    Why this matters: A name-only match could allow a model variant with different capabilities.
    Setup summary: Configure an allowlist entry with the same name but different capabilities.
    """
    default_model = _make_model("default-model")
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            switchable_language_models=[
                {
                    "displayName": "Selected Model",
                    "languageModel": _make_model(
                        "selected-model",
                        capabilities=[ModelCapabilities.STREAMING],
                    ),
                }
            ],
            language_model=default_model,
            tools=[],
        )
    )

    with pytest.raises(
        ValueError,
        match="User model choice 'selected-model' is not allowed for this space.",
    ):
        _apply_model_choice_override(
            event=_make_event(selected_model, has_model_choice_override=True),
            logger=MagicMock(),
            config=config,
        )

    assert config.space.language_model is default_model


@pytest.mark.ai
def test_model_choice_rejects_selected_model_when_missing_from_allowlist() -> None:
    """
    Purpose: Verify switchable_language_models blocks unlisted per-message model choices.
    Why this matters: User-controlled model overrides must not bypass the space allowlist.
    Setup summary: Configure an allowlist without the selected model; assert validation fails.
    """
    default_model = _make_model("default-model")
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            switchable_language_models=[
                {
                    "displayName": "Allowed Model",
                    "languageModel": _make_model("allowed-model"),
                }
            ],
            language_model=default_model,
            tools=[],
        )
    )

    with pytest.raises(
        ValueError,
        match="User model choice 'selected-model' is not allowed for this space.",
    ):
        _apply_model_choice_override(
            event=_make_event(selected_model, has_model_choice_override=True),
            logger=MagicMock(),
            config=config,
        )

    assert config.space.language_model is default_model


@pytest.mark.ai
def test_model_choice_removes_code_interpreter_when_selected_model_lacks_responses_api() -> (
    None
):
    """
    Purpose: Verify Code Interpreter is removed when the selected model lacks Responses API support.
    Why this matters: Code Interpreter cannot run on models without RESPONSES_API and must not be exposed.
    Setup summary: Start with a Responses-capable default plus Code Interpreter; select a non-Responses model.
    """
    default_model = _make_model(
        "default-model",
        capabilities=[
            ModelCapabilities.CHAT_COMPLETIONS_API,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.RESPONSES_API,
            ModelCapabilities.STREAMING,
        ],
    )
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            language_model=default_model,
            tools=[
                ToolBuildConfig(
                    name=OpenAIBuiltInToolName.CODE_INTERPRETER,
                    configuration=CodeInterpreterExtendedConfig(),
                )
            ],
        )
    )
    assert config.agent.experimental.responses_api_config.use_responses_api is True

    config = _apply_model_choice_override(
        event=_make_event(selected_model, has_model_choice_override=True),
        logger=MagicMock(),
        config=config,
    )

    assert config.space.language_model == selected_model
    assert config.space.tools == []
    assert config.agent.experimental.responses_api_config.use_responses_api is False


@pytest.mark.ai
def test_model_choice_rejects_open_file_tool_when_selected_model_lacks_responses_api() -> (
    None
):
    """
    Purpose: Verify model overrides cannot leave OpenFile enabled without Responses API.
    Why this matters: OpenFile depends on Responses API payload handling and would fail at runtime.
    Setup summary: Start with a valid OpenFile config; select a non-Responses model and assert validation fails.
    """
    default_model = _make_model(
        "default-model",
        capabilities=[
            ModelCapabilities.CHAT_COMPLETIONS_API,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.RESPONSES_API,
            ModelCapabilities.STREAMING,
        ],
    )
    selected_model = _make_model("selected-model")
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            language_model=default_model,
            tools=[],
        ),
        agent={
            "experimental": {
                "responses_api_config": {"use_responses_api": True},
                "open_file_tool_config": OpenFileToolConfig(enabled=True),
            }
        },
    )
    assert config.agent.experimental.open_file_tool_config.enabled is True
    assert config.agent.experimental.responses_api_config.use_responses_api is True

    with pytest.raises(
        ValueError,
        match="open_file_tool_config.enabled requires the Responses API",
    ):
        _apply_model_choice_override(
            event=_make_event(selected_model, has_model_choice_override=True),
            logger=MagicMock(),
            config=config,
        )

    assert config.agent.experimental.responses_api_config.use_responses_api is True


@pytest.mark.ai
def test_model_choice_refreshes_search_tool_token_limits() -> None:
    """
    Purpose: Verify model overrides refresh token limits on search tool configs.
    Why this matters: Search tools budget source tokens from the active model's context window.
    Setup summary: Start with a larger model; select a smaller one and assert tool configs follow it.
    """
    default_model = _make_model("default-model")
    selected_model = _make_model("selected-model")
    selected_model.token_limits.token_limit_input = 4_000
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            allow_model_switching=True,
            language_model=default_model,
            tools=[
                ToolBuildConfig(
                    name=InternalSearchTool.name,
                    configuration=InternalSearchConfig(),
                ),
                ToolBuildConfig(
                    name=WebSearchTool.name,
                    configuration=WebSearchConfig(),
                ),
            ],
        ),
        agent={
            "experimental": {
                "retrieve_search_scope_config": RetrieveSearchScopeConfig(enabled=True),
            }
        },
    )

    config = _apply_model_choice_override(
        event=_make_event(selected_model, has_model_choice_override=True),
        logger=MagicMock(),
        config=config,
    )

    token_limits_by_tool_name = {
        tool.name: tool.configuration.language_model_max_input_tokens
        for tool in config.space.tools
        if tool.name
        in {
            InternalSearchTool.name,
            WebSearchTool.name,
            RetrieveSearchScopeTool.name,
        }
    }
    assert token_limits_by_tool_name == {
        InternalSearchTool.name: 4_000,
        WebSearchTool.name: 4_000,
        RetrieveSearchScopeTool.name: 4_000,
    }


@pytest.mark.ai
def test_set_input_context_size_skips_disabled_search_tool_with_base_config() -> None:
    """
    Purpose: Verify a disabled search tool demoted to BaseToolConfig does not crash config load.
    Why this matters: A search tool with an invalid stored config is demoted (is_enabled=False,
    BaseToolConfig); set_input_context_size must skip it instead of raising AttributeError.
    Setup summary: Provide a disabled WebSearch tool that demotes to BaseToolConfig; assert no crash.
    """
    web_search_tool = ToolBuildConfig(
        name=WebSearchTool.name,
        is_enabled=False,
        configuration=BaseToolConfig(),
    )
    # The wrong config type for a WebSearch tool demotes it to disabled + BaseToolConfig.
    assert web_search_tool.is_enabled is False
    assert not hasattr(web_search_tool.configuration, "language_model_max_input_tokens")

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            language_model=_make_model("default-model"),
            tools=[web_search_tool],
        )
    )

    disabled_tool = next(
        tool for tool in config.space.tools if tool.name == WebSearchTool.name
    )
    assert disabled_tool.is_enabled is False
    assert not hasattr(disabled_tool.configuration, "language_model_max_input_tokens")
