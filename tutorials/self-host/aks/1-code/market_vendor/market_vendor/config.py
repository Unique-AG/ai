# ============================================================================
# MOCK FILE - SDK DEPLOYMENT EXAMPLE
# ============================================================================
# This is a mock configuration file for demonstration purposes only.
# It shows how an SDK assistant configuration might be structured.
# This file is NOT production-ready and should be adapted to your specific
# configuration requirements.
# ============================================================================

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from unique_toolkit.language_model import LanguageModelName


class MarketVendorConfig(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    language_model_name: LanguageModelName = (
        LanguageModelName.AZURE_GPT_4_TURBO_2024_0409
    )
