from typing import Annotated

from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import (
    NoneToDefault,
    get_configuration_dict,
)


class DocxGeneratorConfig(BaseModel):
    model_config = get_configuration_dict()

    template_content_id: Annotated[str, NoneToDefault] = Field(
        default="",
        description="The content id of the template file uploaded to the knowledge base.",
    )
