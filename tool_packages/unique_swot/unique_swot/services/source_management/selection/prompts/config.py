from pathlib import Path

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.utils import load_template

PARENT_DIR = Path(__file__).parent


class SourceSelectionPromptConfig(BaseModel):
    model_config = get_configuration_dict()

    system_prompt: str = Field(
        default_factory=lambda: load_template(PARENT_DIR, "system_prompt.j2"),
        description="The system prompt for the source selection.",
    )
    user_prompt: str = Field(
        default_factory=lambda: load_template(PARENT_DIR, "user_prompt.j2"),
        description="The user prompt for the source selection.",
    )
