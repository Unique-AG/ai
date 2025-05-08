from unique_toolkit.evaluators.config import EvaluationMetricConfig
from unique_toolkit.evaluators.context_relevancy.prompts import (
    CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
    CONTEXT_RELEVANCY_METRIC_USER_MSG,
)
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricInputFieldName,
    EvaluationMetricName,
)
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.service import LanguageModelName

SYSTEM_MSG_KEY = "systemPrompt"
USER_MSG_KEY = "userPrompt"

# Required input fields for context relevancy evaluation
context_relevancy_required_input_fields = [
    EvaluationMetricInputFieldName.INPUT_TEXT,
    EvaluationMetricInputFieldName.CONTEXT_TEXTS,
]


default_config = EvaluationMetricConfig(
    enabled=False,
    name=EvaluationMetricName.CONTEXT_RELEVANCY,
    language_model=LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_35_TURBO_0125
    ),
    score_to_emoji={"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"},
    custom_prompts={
        SYSTEM_MSG_KEY: CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
        USER_MSG_KEY: CONTEXT_RELEVANCY_METRIC_USER_MSG,
    },
)
