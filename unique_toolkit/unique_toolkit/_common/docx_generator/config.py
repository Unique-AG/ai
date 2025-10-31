from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class DocxGeneratorConfig(BaseModel):
    model_config = get_configuration_dict()

    template_content_id: str = Field(
        default="",
        description="The content ID of the template file to be found in the templateScopeId. If not provided, the default template will be used.",
    )

    template_fields: dict = Field(
        default={},
        description="The fields to be replaced in the template.",
    )
