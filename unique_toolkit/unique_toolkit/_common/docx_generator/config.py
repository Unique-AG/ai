from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Self

from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class DocxGeneratorConfig(BaseModel):
    model_config = get_configuration_dict()

    enabled: bool = Field(
        default=True,
        description="Whether to enable the docx generator.",
    )
    upload_suffix: str = Field(
        default="_report_output.docx",
        description="The suffix of the uploaded file.",
    )
    upload_scope_id: str | SkipJsonSchema[None] = Field(
        default=None,
        description="The scope ID where the generated DOCX file will be uploaded. If not provided and upload_to_chat is False, an error will be raised.",
    )
    upload_to_chat: bool = Field(
        default=True,
        description="Whether to upload the file to the chat.",
    )

    template_content_id: str | SkipJsonSchema[None] = Field(
        default=None,
        description="The content ID of the template file to be found in the templateScopeId. If not provided, the default template will be used.",
    )

    template_name: str = Field(
        default="template.docx",
        description="The name of the template file to be found in the templateScopeId. If not provided, or match no file, the default template will be used.",
        deprecated="Please use content_id instead",
    )
    template_scope_id: str | SkipJsonSchema[None] = Field(
        default=None,
        description="The scope ID where the template file is stored. If not provided, the default template will be used.",
        deprecated="Please use content_id instead",
    )

    template_fields: dict[str, object] = Field(
        default_factory=lambda: {
            "date": datetime.now().strftime("%d/%m/%Y"),
            "document_title": "Template Document",
        },
        description="The fields to be replaced in the template.",
    )

    skip_ingestion: bool = Field(
        default=True,
        description="Whether to skip the ingestion of the file.",
    )

    @field_validator("template_fields", mode="after", check_fields=True)
    def validate_template_fields(cls, v: dict[str, object]) -> dict[str, object]:
        for key, value in v.items():
            if value == "CURRENT_DATE":
                v[key] = datetime.now().strftime("%d/%m/%Y")
            else:
                v[key] = value
        return v

    @model_validator(mode="after")
    def validate_upload_to_chat(self) -> Self:
        if not self.enabled:
            return self

        if not self.upload_to_chat and not self.upload_scope_id:
            raise ValueError("Either upload_to_chat or upload_scope_id must be set")
        return self
