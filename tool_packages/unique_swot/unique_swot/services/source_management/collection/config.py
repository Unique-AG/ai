from pydantic import BaseModel, Field
from unique_toolkit._common.docx_generator import DocxGeneratorConfig
from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class EarningsCallConfig(BaseModel):
    model_config = get_configuration_dict()

    upload_scope_id: str = Field(
        default="",
        description="The scope id to use for uploading the earnings calls.",
    )

    docx_renderer_config: DocxGeneratorConfig = Field(
        default_factory=DocxGeneratorConfig,
        description="The configuration for the earnings call docx renderer.",
    )
