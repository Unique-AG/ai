# default schema follows logic in node-ingestion-worker: https://github.com/Unique-AG/monorepo/blob/76b4923611199a80abf9304639b3aa0538ec41ed/node/apps/node-ingestion-worker/src/ingestors/lib/text-manipulations.ts#L181C17-L181C28
from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict

SECTIONS = {
    "document": "<|document|>{}<|/document|>\n",
}


class SourceFormatConfig(BaseModel):
    model_config = get_configuration_dict()
    sections: dict[str, str] = Field(
        default=SECTIONS,
        description="Metadata sections to add to the chunks. Each entry is a key-value pair where the key is the metadata key and the value is the template to format the metadata in the chunk text.",
    )

    @staticmethod
    def template_to_pattern(template: str) -> str:
        """Convert a template string into a regex pattern."""
        return template.replace("{}", "(.*?)").replace("|", r"\|")
