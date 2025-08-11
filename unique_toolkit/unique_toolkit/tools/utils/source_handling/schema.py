

# default schema follows logic in node-ingestion-worker: https://github.com/Unique-AG/monorepo/blob/76b4923611199a80abf9304639b3aa0538ec41ed/node/apps/node-ingestion-worker/src/ingestors/lib/text-manipulations.ts#L181C17-L181C28
from pydantic import BaseModel

from unique_toolkit.tools.config import get_configuration_dict


SOURCE_TEMPLATE = "<source${index}>${document}${info}${text}</source${index}>"
SECTIONS = {
    "document": "<|document|>{}<|/document|>\n",
    "info": "<|info|>{}<|/info|>\n",
}


class SourceFormatConfig(BaseModel):
    model_config = get_configuration_dict()
    source_template: str = SOURCE_TEMPLATE
    sections: dict[str, str] = SECTIONS

    @staticmethod
    def template_to_pattern(template: str) -> str:
        """Convert a template string into a regex pattern."""
        return template.replace("{}", "(.*?)").replace("|", r"\|")
