"""Tests for the capability-driven Responses API validator.

``UniqueAIConfig.enable_responses_api_when_model_requires_it`` forces the
Responses API whenever ``LanguageModelInfo.requires_responses_api_for_tool_calling``
is true, i.e. when the model does not support chat completions at all or is
marked with ``ModelCapabilities.TOOL_CALLING_REQUIRES_RESPONSES_API`` because the
provider rejects function tools combined with reasoning on ``/v1/chat/completions``
(GPT-5.4, GPT-5.5, GPT-5.6 and their LiteLLM mirrors).

Tracked in Jira: UN-20123.

These tests live in the top-level ``tests/`` directory; CI test and coverage use
the same pytest discovery from the package root.
"""

from __future__ import annotations

import pytest
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

from unique_orchestrator.config import (
    ExperimentalConfig,
    ResponsesApiConfig,
    UniqueAIConfig,
    UniqueAISpaceConfig,
)

MARKED_MODELS = [
    LanguageModelName.AZURE_GPT_54_2026_0305,
    LanguageModelName.AZURE_GPT_55_2026_0424,
    LanguageModelName.AZURE_GPT_55_PRO_2026_0424,
    LanguageModelName.AZURE_GPT_56_SOL_2026_0709,
    LanguageModelName.AZURE_GPT_56_TERRA_2026_0709,
    LanguageModelName.AZURE_GPT_56_LUNA_2026_0709,
    LanguageModelName.LITELLM_OPENAI_GPT_54,
    LanguageModelName.LITELLM_OPENAI_GPT_54_THINKING,
    LanguageModelName.LITELLM_OPENAI_GPT_55,
    LanguageModelName.LITELLM_OPENAI_GPT_55_PRO,
    LanguageModelName.LITELLM_OPENAI_GPT_56_SOL,
    LanguageModelName.LITELLM_OPENAI_GPT_56_TERRA,
    LanguageModelName.LITELLM_OPENAI_GPT_56_LUNA,
]

RESPONSES_ONLY_MODELS = [
    LanguageModelName.AZURE_GPT_5_PRO_2025_1006,
    LanguageModelName.AZURE_GPT_54_PRO_2026_0305,
]

UNAFFECTED_MODELS = [
    LanguageModelName.AZURE_GPT_4o_2024_1120,
    LanguageModelName.AZURE_GPT_5_2025_0807,
    LanguageModelName.AZURE_GPT_51_2025_1113,
]

CODE_INTERPRETER_TOOL = ToolBuildConfig(
    name=OpenAIBuiltInToolName.CODE_INTERPRETER,
    configuration=CodeInterpreterExtendedConfig(),
)


def _make_custom_model(capabilities: list[ModelCapabilities]) -> LanguageModelInfo:
    return LanguageModelInfo(
        name="some-custom-model",
        provider=LanguageModelProvider.CUSTOM,
        version="test",
        capabilities=capabilities,
        token_limits=LanguageModelTokenLimits(
            token_limit_input=10_000, token_limit_output=2_000
        ),
    )


@pytest.mark.parametrize("model_name", MARKED_MODELS + RESPONSES_ONLY_MODELS)
def test_enables_responses_api_for_models_that_require_it(
    model_name: LanguageModelName,
) -> None:
    """Models requiring the Responses API for tool calling are routed to it."""
    model = LanguageModelInfo.from_name(model_name)

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=model, tools=[]),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is True


@pytest.mark.parametrize("model_name", MARKED_MODELS)
def test_enables_responses_api_regardless_of_configured_tools(
    model_name: LanguageModelName,
) -> None:
    """The transport requirement is independent of configured tools."""
    model = LanguageModelInfo.from_name(model_name)

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            language_model=model,
            tools=[CODE_INTERPRETER_TOOL],
        ),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is True


@pytest.mark.parametrize("model_name", MARKED_MODELS)
def test_enables_responses_api_regardless_of_reasoning_effort(
    model_name: LanguageModelName,
) -> None:
    """Even an explicit ``reasoning_effort: none`` keeps the model on Responses."""
    model = LanguageModelInfo.from_name(model_name)

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=model, tools=[]),
        agent={
            "experimental": ExperimentalConfig(
                additional_llm_options={"reasoning_effort": "none"},
            )
        },
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is True


@pytest.mark.parametrize("model_name", UNAFFECTED_MODELS)
def test_does_not_enable_responses_api_for_unaffected_models(
    model_name: LanguageModelName,
) -> None:
    """Models that support tools + reasoning on chat completions stay there."""
    model = LanguageModelInfo.from_name(model_name)

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=model, tools=[]),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is False


def test_does_not_enable_responses_api_for_unmarked_custom_model() -> None:
    """A Responses-capable model that also supports chat completions is untouched."""
    model = _make_custom_model(
        [
            ModelCapabilities.CHAT_COMPLETIONS_API,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.STREAMING,
            ModelCapabilities.RESPONSES_API,
        ]
    )

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=model, tools=[]),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is False


def test_enables_responses_api_for_marked_custom_model() -> None:
    """The marker is honoured for custom models (e.g. via LANGUAGE_MODEL_INFOS)."""
    model = _make_custom_model(
        [
            ModelCapabilities.CHAT_COMPLETIONS_API,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.STREAMING,
            ModelCapabilities.RESPONSES_API,
            ModelCapabilities.TOOL_CALLING_REQUIRES_RESPONSES_API,
        ]
    )

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=model, tools=[]),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is True


def test_marker_is_ignored_when_model_lacks_responses_api_support() -> None:
    """Without ``RESPONSES_API`` the marker must not force an unsupported transport."""
    model = _make_custom_model(
        [
            ModelCapabilities.CHAT_COMPLETIONS_API,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.STREAMING,
            ModelCapabilities.TOOL_CALLING_REQUIRES_RESPONSES_API,
        ]
    )

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=model, tools=[]),
        agent={
            "experimental": ExperimentalConfig(
                responses_api_config=ResponsesApiConfig(use_responses_api=True),
            )
        },
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is False


@pytest.mark.parametrize("model_name", MARKED_MODELS)
def test_keeps_responses_api_enabled_when_already_enabled(
    model_name: LanguageModelName,
) -> None:
    """The validator must remain idempotent."""
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
