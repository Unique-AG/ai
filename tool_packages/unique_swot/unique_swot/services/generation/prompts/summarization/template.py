from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

_PROMPTS_DIR = Path(__file__).parent

# Create Jinja2 environment
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)

# Load the base template
_base_template = _jinja_env.get_template("base_template.j2")


class SummarizationPromptTemplate(BaseModel):
    """
    Template model for generating SWOT component summarization prompts.

    This model holds all the component-specific configuration needed to render
    a complete summarization prompt from the base Jinja2 template.
    """

    # Component identification
    component_name: str = Field(
        description="Capitalized component name (e.g., 'Opportunity', 'Strength')"
    )
    component_singular: str = Field(
        description="Lowercase singular form (e.g., 'opportunity', 'strength')"
    )
    component_plural: str = Field(
        description="Lowercase plural form (e.g., 'opportunities', 'strengths')"
    )

    # Scope and context
    scope_type: str = Field(
        description="Type of factors being analyzed (e.g., 'external conditions', 'internal advantages')"
    )
    scope_description: str = Field(
        description="Description of what constitutes similar items for merging"
    )
    scope_context: str = Field(
        description="Context for distinct items (e.g., 'external environment', 'organization's internal capabilities')"
    )

    # Quality standards (optional)
    quality_focus: str | None = Field(
        default=None, description="Primary quality focus statement (optional)"
    )
    additional_quality_standard: str | None = Field(
        default=None, description="Additional quality standard or guideline (optional)"
    )
    additional_merge_guideline: str | None = Field(
        default=None,
        description="Additional guideline for merging similar items (optional)",
    )

    # Examples for understanding
    merge_examples: list[str] = Field(
        description="List of examples showing what should be merged"
    )
    distinct_examples: list[str] = Field(
        description="List of examples showing what should remain separate"
    )

    # Output configuration
    output_scope: str = Field(description="Scope description for output expectations")
    output_context: str = Field(
        description="Context description for what the output should present"
    )
    additional_expectations: list[str] = Field(
        default_factory=list, description="Additional output expectations (optional)"
    )

    # Format example
    example_title: str = Field(
        description="Example title for the output format section"
    )
    example_bullets: list[str] = Field(
        description="List of example bullet points showing the desired format"
    )
    example_reasoning: str = Field(
        description="Example of bold reasoning text extracted from the first example bullet"
    )
    bullet_focus: str = Field(
        description="What each bullet should focus on (e.g., 'implication', 'consequence', 'impact')"
    )

    def render(self) -> str:
        """
        Render the complete prompt by applying this configuration to the base template.

        Returns:
            str: The fully rendered prompt text ready for use as a system prompt
        """
        return _base_template.render(**self.model_dump())
