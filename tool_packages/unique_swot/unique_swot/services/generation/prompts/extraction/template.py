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


class QualificationCategory(BaseModel):
    """A category of factors that qualify for a SWOT component."""

    name: str = Field(
        description="Category name (e.g., 'Market Trends', 'Core Competencies')"
    )
    description: str = Field(
        description="Description of what falls under this category"
    )


class ExtractionPromptTemplate(BaseModel):
    """
    Template model for generating SWOT component extraction prompts.

    This model holds all the component-specific configuration needed to render
    a complete extraction prompt from the base Jinja2 template.
    """

    # Component identification
    component_name: str = Field(
        description="Singular component name (e.g., 'Opportunity', 'Strength')"
    )
    component_name_plural: str = Field(
        description="Plural component name (e.g., 'Opportunities', 'Strengths')"
    )
    component_singular: str = Field(
        description="Lowercase singular form (e.g., 'opportunity', 'strength')"
    )
    article: str = Field(
        description="Article to use before component name ('a' or 'an')"
    )

    # Scope and nature
    internal_external: str = Field(
        description="Whether factors are 'internal' or 'external'"
    )
    scope_type: str = Field(
        description="Type of factors (e.g., 'external positive factors', 'internal negative factors')"
    )
    scope_description: str = Field(
        description="Description of what these factors do or represent"
    )
    scope_context: str | None = Field(
        default=None, description="Additional context about the scope (optional)"
    )

    # Qualification criteria
    qualification_categories: list[QualificationCategory] = Field(
        description="List of categories that qualify for this component"
    )
    key_distinction: str = Field(
        description="Key distinction statement explaining what this component represents"
    )

    # Guidelines
    title_guideline: str = Field(description="What the title should capture")
    explanation_focus: str = Field(
        description="Focus label for explanation guideline (e.g., 'Provide Deep Context', 'Explain the Benefit')"
    )
    explanation_details: str = Field(
        description="Details about what the explanation should include"
    )
    evidence_requirement: str = Field(
        description="What needs evidence (e.g., 'claims', 'assessments')"
    )
    evidence_type: str = Field(
        description="Type of evidence needed (e.g., 'data, metrics, or examples', 'examples, data, or specific instances')"
    )
    objectivity_guideline: str = Field(
        description="Guideline for maintaining objectivity"
    )
    distinction_category: str = Field(
        description="The other SWOT category to distinguish from"
    )
    distinction_explanation: str = Field(
        description="Explanation of how to distinguish from the other category"
    )

    def render(self) -> str:
        """
        Render the complete prompt by applying this configuration to the base template.

        Returns:
            str: The fully rendered prompt text ready for use as a system prompt
        """
        return _base_template.render(**self.model_dump())
