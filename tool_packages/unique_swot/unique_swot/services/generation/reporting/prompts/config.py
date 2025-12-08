from pathlib import Path

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.utils import load_template

PARENT_DIR = Path(__file__).parent


class ReportingPromptConfig(BaseModel):
    model_config = get_configuration_dict()

    opportunities: str = Field(
        default_factory=lambda: load_template(PARENT_DIR, "opportunities.j2"),
        description="The prompt for the opportunities extraction.",
    )
    weaknesses: str = Field(
        default_factory=lambda: load_template(PARENT_DIR, "weaknesses.j2"),
        description="The prompt for the weaknesses extraction.",
    )
    strengths: str = Field(
        default_factory=lambda: load_template(PARENT_DIR, "strengths.j2"),
        description="The prompt for the strengths extraction.",
    )
    threats: str = Field(
        default_factory=lambda: load_template(PARENT_DIR, "threats.j2"),
        description="The prompt for the threats extraction.",
    )
    user_prompt: str = Field(
        default_factory=lambda: load_template(PARENT_DIR, "user_prompt.j2"),
        description="The prompt for the user prompt.",
    )
