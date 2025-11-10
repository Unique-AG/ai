from pydantic import BaseModel, Field

from unique_toolkit.agentic.tools.config import get_configuration_dict


class FeatureExtendedSourceSerialization(BaseModel):
    """Mixin for experimental feature in Source serialization"""

    model_config = get_configuration_dict()
    full_sources_serialize_dump: bool = Field(
        default=False,
        description="Whether to include the full source object in the tool response. If True, includes the full Source object. If False, uses the old format with only source_number and content.",
    )
