from typing import Any

from pydantic import BaseModel, Field
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

from unique_stock_ticker.detection.memory import StockTickerMemoryConfig


class StockTickerDetectionConfig(BaseModel):
    model_config = get_configuration_dict()
    language_model: LMI = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_35_TURBO_0125,
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    memory_config: StockTickerMemoryConfig = StockTickerMemoryConfig()
