from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.source_management.collection.config import EarningsCallConfig
from unique_swot.services.source_management.iteration.date_relevancy import (
    DateRelevancySourceIteratorConfig,
)


class SourceManagementConfig(BaseModel):
    model_config = get_configuration_dict()

    earnings_call_config: EarningsCallConfig = Field(
        default_factory=EarningsCallConfig,
        description="The configuration for the earnings call management.",
    )

    date_relevancy_config: DateRelevancySourceIteratorConfig = Field(
        default_factory=DateRelevancySourceIteratorConfig,
        description="The configuration for the date relevancy.",
    )
