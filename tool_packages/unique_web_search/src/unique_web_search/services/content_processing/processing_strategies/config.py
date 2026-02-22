from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcessorConfig,
)
from unique_web_search.services.content_processing.processing_strategies.truncate import (
    TruncateConfig,
)


class ProcessingStrategiesConfig(BaseModel):
    model_config = get_configuration_dict()

    truncate: TruncateConfig = Field(
        default_factory=TruncateConfig,
        title="Content Length Limit",
        description="Limit web page content to a maximum length. Useful to prevent very long pages from using too many resources.",
    )

    llm_processor: LLMProcessorConfig = Field(
        default_factory=LLMProcessorConfig,
        title="AI Content Summarization",
        description="Use AI to summarize and compress long web page content, extracting only the most relevant information.",
    )
