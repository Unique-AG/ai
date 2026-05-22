from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterExtendedConfig,
)
from unique_toolkit.agentic.tools.tool import ToolBuildConfig
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelProvider,
    ModelCapabilities,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenLimits

from unique_orchestrator.config import UniqueAIConfig, UniqueAISpaceConfig
from unique_orchestrator.unique_ai_builder import _apply_model_choice_override


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
def test_space_config_accepts_allow_user_model_selection_alias() -> None:
    """
    Purpose: Verify backend camelCase config populates the Python space config flag.
    Why this matters: The node backend forwards allowUserModelSelection into the event payload.
    Setup summary: Validate camelCase input; assert the snake_case field is enabled.
    """
    config = UniqueAISpaceConfig.model_validate(
        {
            "allowUserModelSelection": True,
            "tools": [],
        }
    )

    assert config.allow_user_model_selection is True


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
            allow_user_model_selection=True,
            language_model=default_model,
            tools=[],
        )
    )

    _apply_model_choice_override(
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
            allow_user_model_selection=False,
            language_model=default_model,
            tools=[],
        )
    )

    _apply_model_choice_override(
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
            allow_user_model_selection=True,
            language_model=default_model,
            tools=[],
        )
    )

    _apply_model_choice_override(
        event=_make_event(selected_model, has_model_choice_override=True),
        logger=MagicMock(),
        config=config,
    )

    assert config.space.language_model is selected_model


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
            allow_user_model_selection=True,
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

    _apply_model_choice_override(
        event=_make_event(selected_model, has_model_choice_override=True),
        logger=MagicMock(),
        config=config,
    )

    assert config.space.language_model is selected_model
    assert config.space.tools == []
    assert config.agent.experimental.responses_api_config.use_responses_api is False
