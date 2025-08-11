

from unique_toolkit.evaluators.config import EvaluationMetricConfig
from pydantic import BaseModel
from unique_toolkit.unique_toolkit.evaluators.hallucination.constants import HallucinationConfig
from unique_toolkit.unique_toolkit.tools.config import get_configuration_dict


class EvaluationConfig(BaseModel):
    model_config = get_configuration_dict()
    max_review_steps: int = 3
    hallucination_config: HallucinationConfig = HallucinationConfig()
