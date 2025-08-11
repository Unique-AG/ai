import pytest
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)
from unique_toolkit.unique_toolkit.base_agents.loop_agent.config import LoopAgentConfig, LoopAgentTokenLimitsConfig



LANGUAGE_MODELS = []
for name in LanguageModelName:
    LANGUAGE_MODELS.append(LanguageModelInfo.from_name(name))


@pytest.mark.parametrize(
    "language_model",
    LANGUAGE_MODELS,
)
def test_sets_language_model_in_token_limits_config(language_model):
    config = LoopAgentConfig(language_model=language_model)
    assert config.language_model == language_model


@pytest.mark.parametrize(
    "language_model",
    LANGUAGE_MODELS,
)
def test_set_percentage_of_input_token_for_history(language_model):
    config = LoopAgentTokenLimitsConfig(
        language_model=language_model,
        percent_of_max_tokens_for_history=0.3,
    )
    assert (
        abs(
            config.max_history_tokens
            - round(language_model.token_limits.token_limit_input * 0.3)
        )
        < 5
    )


@pytest.mark.parametrize(
    "language_model",
    LANGUAGE_MODELS,
)
def test_get_unknown_tool_raises_error(language_model):
    config = LoopAgentConfig(language_model=language_model)
    with pytest.raises(ValueError):
        config.get_tool_config("UNKNOWN_TOOL")  # type: ignore

