from pydantic import BaseModel

from unique_toolkit.agentic.tools.config import get_configuration_dict


class FeatureExtendedSourceSerialization(BaseModel):
    """Mixin for experimental feature in Source serialization"""

    model_config = get_configuration_dict()
