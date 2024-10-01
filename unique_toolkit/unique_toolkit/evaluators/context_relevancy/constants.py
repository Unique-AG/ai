from unique_toolkit.evaluators.config import EvaluationMetricConfig
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricName,
)
from unique_toolkit.language_model.infos import LanguageModel
from unique_toolkit.language_model.service import LanguageModelName

from .prompts import (
    CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
    CONTEXT_RELEVANCY_METRIC_USER_MSG,
)

SYSTEM_MSG_KEY = "systemPrompt"
USER_MSG_KEY = "userPrompt"

# Required input fields for context relevancy evaluation
context_relevancy_required_input_fields = [
    "input_text",
    "output_text",
    "context_texts",
]


default_config = EvaluationMetricConfig(
    enabled=False,
    name=EvaluationMetricName.CONTEXT_RELEVANCY,
    language_model=LanguageModel(LanguageModelName.AZURE_GPT_35_TURBO_0613),
    score_to_emoji={"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"},
    custom_prompts={
        SYSTEM_MSG_KEY: CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
        USER_MSG_KEY: CONTEXT_RELEVANCY_METRIC_USER_MSG,
    },
)
