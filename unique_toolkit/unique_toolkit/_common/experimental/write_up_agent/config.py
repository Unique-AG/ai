from pydantic import BaseModel, Field, field_validator

from unique_toolkit._common.experimental.write_up_agent.services.generation_handler.config import (
    GenerationHandlerConfig,
)
from unique_toolkit._common.experimental.write_up_agent.services.template_handler import (
    default_jinja_template_loader,
)
from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class WriteUpAgentConfig(BaseModel):
    """Configuration for the Write-Up Agent that generates summaries from DataFrame data.

    The agent uses a Jinja template as the single source of truth for data structure.
    The template is parsed to automatically detect grouping columns and data references.
    """

    model_config = get_configuration_dict()

    # Template Configuration (single source of truth)
    template: str = Field(
        default_factory=default_jinja_template_loader,
        description=(
            "Jinja template string that defines the structure of the summary. "
            "The template is parsed to automatically detect grouping columns and data references. "
            "If not provided, loads the default Q&A template. "
            "Example: '{% for g in groups %}## {{ g.section }}{% endfor %}'"
        ),
    )

    generation_handler_config: GenerationHandlerConfig = Field(
        default_factory=GenerationHandlerConfig,
        description="Configuration for the generation handler.",
    )

    @field_validator("template")
    @classmethod
    def validate_template_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Template must not be empty")
        return v
