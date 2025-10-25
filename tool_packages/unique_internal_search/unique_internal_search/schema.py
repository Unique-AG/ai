from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class ChunkMetadataSection(BaseModel):
    model_config = get_configuration_dict()
    """Represents a metadata section with its key and template value."""

    key: str = Field(description="Metadata key to extract from the source")
    template: str = Field(
        description="Template to format the metadata in the chunk text. Use {} as a placeholder in the template for the metadata value."
    )

    @staticmethod
    def pattern_from_template(template: str) -> str:
        """Convert a template string into a regex pattern."""
        return template.replace("{}", "(.*?)").replace("|", r"\|")
