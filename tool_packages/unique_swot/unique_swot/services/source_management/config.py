from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.source_management.collection.config import EarningsCallConfig
from unique_swot.services.source_management.iteration.config import (
    SourceIterationConfig,
)
from unique_swot.services.source_management.selection.config import (
    SourceSelectionConfig,
)


class SourceManagementConfig(BaseModel):
    model_config = get_configuration_dict()

    source_selection_config: SourceSelectionConfig = Field(
        default_factory=SourceSelectionConfig,
        description="The configuration for the source selection.",
    )

    earnings_call_config: EarningsCallConfig = Field(
        default_factory=EarningsCallConfig,
        description="The configuration for the earnings call management.",
    )

    source_iteration_config: SourceIterationConfig = Field(
        default_factory=SourceIterationConfig,
        description="The configuration for the date relevancy.",
    )
