"""Tests for UniqueAIConfig.enable_responses_api_for_gpt_55_and_gpt_55_pro.

GPT-5.5 (AZURE_GPT_55_2026_0424) and GPT-5.5-Pro (AZURE_GPT_55_PRO_2026_0424)
reject requests that combine ``tools`` with ``reasoning_effort`` on
``/v1/chat/completions`` and demand ``/v1/responses``. The validator forces
the Responses API on when either of these models is selected, regardless of
which tools are configured.

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
]

CODE_INTERPRETER_TOOL = ToolBuildConfig(
    name=OpenAIBuiltInToolName.CODE_INTERPRETER,
    configuration=CodeInterpreterExtendedConfig(),
)


def _make_unaffected_model() -> LanguageModelInfo:
    """Build a model that is NOT GPT-5.5(-Pro) but still supports the Responses API.

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
    """When the selected model is GPT-5.5 or GPT-5.5-Pro, the validator must
    flip ``use_responses_api`` to True so the runner routes to ``/v1/responses``."""
    model = LanguageModelInfo.from_name(model_name)

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=model, tools=[]),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is True


@pytest.mark.parametrize("model_name", AFFECTED_MODELS)
def test_enables_responses_api_for_affected_models_with_tools(
    model_name: LanguageModelName,
) -> None:
    """The auto-enable applies even when other tools (e.g. Code Interpreter)
    are configured — the GPT-5.5(-Pro) transport requirement is independent
    of the Code Interpreter validator."""
    model = LanguageModelInfo.from_name(model_name)

    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(
            language_model=model,
            tools=[CODE_INTERPRETER_TOOL],
        ),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is True


def test_does_not_enable_responses_api_for_other_models() -> None:
    """When the selected model is neither GPT-5.5 nor GPT-5.5-Pro, the validator
    must be a no-op even if the model supports the Responses API. Otherwise the
    TEMP FIX could mask real configuration issues for unaffected models."""
    config = UniqueAIConfig(
        space=UniqueAISpaceConfig(language_model=_make_unaffected_model(), tools=[]),
    )

    assert config.agent.experimental.responses_api_config.use_responses_api is False


@pytest.mark.parametrize("model_name", AFFECTED_MODELS)
def test_keeps_responses_api_enabled_when_already_enabled(
    model_name: LanguageModelName,
) -> None:
    """When ``use_responses_api`` is already True for an affected model, the
    validator must leave it True — i.e. it is idempotent for those models."""
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
