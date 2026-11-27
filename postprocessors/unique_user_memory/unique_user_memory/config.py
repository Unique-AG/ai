from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.default_language_model import (
    DEFAULT_LANGUAGE_MODEL,
)
from unique_toolkit.language_model.infos import LanguageModelInfo


class UserMemoryConfig(BaseModel):
    model_config = get_configuration_dict()

    use_orchestrator_language_model: bool = Field(
        default=True,
        description=(
            "Use the orchestrator's language model to update memory. "
            "Turn off to use the language model configured below instead."
        ),
    )
    language_model: LMI = Field(
        default=LanguageModelInfo.from_name(DEFAULT_LANGUAGE_MODEL),
        description="Language model used to update memory when the orchestrator's model is not used.",
    )
    max_tokens: Annotated[int, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        default=2000,
        ge=500,
        le=8000,
        description="Maximum size of the memory profile, in tokens.",
    )
    consolidation_gate_enabled: bool = Field(
        default=True,
        description="Skip memory updates for turns that add no new information, to save cost.",
    )
    root_folder: Annotated[str, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        default="user-memory",
        min_length=1,
        # Name used under the user's own home folder (UN-24823); also read
        # as a legacy fallback for users not yet migrated (UN-24896).
        description="Folder used to store the user's memory profile.",
    )
