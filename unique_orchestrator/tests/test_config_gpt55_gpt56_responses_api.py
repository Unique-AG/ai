"""Tests for the GPT-5.5 and GPT-5.6 Responses API validator.

These models reject requests that combine ``tools`` with ``reasoning_effort``
on ``/v1/chat/completions`` and demand ``/v1/responses``. The validator forces
the Responses API on regardless of which tools are configured.

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

AFFECTED_MODELS = [
    LanguageModelName.AZURE_GPT_55_2026_0424,
    LanguageModelName.AZURE_GPT_55_PRO_2026_0424,
    LanguageModelName.AZURE_GPT_56_SOL_2026_0709,
    LanguageModelName.AZURE_GPT_56_TERRA_2026_0709,
    LanguageModelName.AZURE_GPT_56_LUNA_2026_0709,
    LanguageModelName.LITELLM_OPENAI_GPT_55,
    LanguageModelName.LITELLM_OPENAI_GPT_55_PRO,
    LanguageModelName.LITELLM_OPENAI_GPT_56_SOL,
    LanguageModelName.LITELLM_OPENAI_GPT_56_TERRA,
    LanguageModelName.LITELLM_OPENAI_GPT_56_LUNA,
]

CODE_INTERPRETER_TOOL = ToolBuildConfig(
    name=OpenAIBuiltInToolName.CODE_INTERPRETER,
    configuration=CodeInterpreterExtendedConfig(),
)


def _make_unaffected_model() -> LanguageModelInfo:
    """Build an unrelated model that still supports the Responses API.

    Used to assert the validator only auto-enables for the specific affected
    models — never for unrelated models, even when capabilities would allow it.
    """
    return LanguageModelInfo(
        name="some-other-model",
        provider=LanguageModelProvider.AZURE,
        version="test",
        capabilities=[
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.STREAMING,
            ModelCapabilities.RESPONSES_API,
        ],
        token_limits=LanguageModelTokenLimits(
            token_limit_input=10_000, token_limit_output=2_000
        ),
    )


@pytest.mark.parametrize("model_name", AFFECTED_MODELS)
def test_enables_responses_api_for_affected_models(
    model_name: LanguageModelName,
) -> None:
    """Affected models must route through ``/v1/responses``."""
    model = LanguageModelInfo.from_name(model_name)

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=model, tools=[]),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is True


@pytest.mark.parametrize("model_name", AFFECTED_MODELS)
def test_enables_responses_api_for_affected_models_with_tools(
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


def test_does_not_enable_responses_api_for_other_models() -> None:
    """The validator must not affect unrelated Responses-capable models."""
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=_make_unaffected_model(), tools=[]),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is False


@pytest.mark.parametrize("model_name", AFFECTED_MODELS)
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
