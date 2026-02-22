from pydantic import BaseModel, Field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.services.content_processing.cleaning.config import (
    CleaningConfig,
)
from unique_web_search.services.content_processing.processing_strategies.config import (
    ProcessingStrategiesConfig,
)


class ContentProcessorConfig(BaseModel):
    model_config = get_configuration_dict()

    chunk_size: int = Field(
        default=1000,
        title="Content Chunk Size",
        description="Maximum size (in characters) of each content piece when splitting long web pages. Smaller values create more pieces; larger values keep more context together.",
    )

    cleaning: CleaningConfig = Field(
        default_factory=CleaningConfig,
        title="Content Cleaning",
        description="Automatic cleanup steps to remove clutter (e.g. navigation menus, cookie banners, URLs) from web page content before it is used.",
    )

    processing_strategies: ProcessingStrategiesConfig = Field(
        default_factory=ProcessingStrategiesConfig,
        title="Content Processing",
        description="Additional processing steps applied to web page content after retrieval, such as shortening or AI-based summarization.",
    )

    @property
    def active_processing_strategies(self) -> list[str]:
        active_cleaning_strategies = []
        if self.cleaning.line_removal.enabled:
            active_cleaning_strategies.append("line_removal")
        if self.cleaning.markdown_transformation.enabled:
            active_cleaning_strategies.append("markdown_transformation")

        active_processing_strategies = []
        if self.processing_strategies.truncate.enabled:
            active_processing_strategies.append("truncate")
        if self.processing_strategies.llm_processor.enabled:
            active_processing_strategies.append("llm_processor")

        return active_cleaning_strategies + active_processing_strategies
