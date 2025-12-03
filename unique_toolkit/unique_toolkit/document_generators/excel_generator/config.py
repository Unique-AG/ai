from pydantic import BaseModel, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class ExcelGeneratorConfig(BaseModel):
    model_config = get_configuration_dict()
    upload_suffix: str = Field(
        default="_answers.xlsx",
        description="The suffix of the uploaded file.",
    )
    upload_scope_id: str | SkipJsonSchema[None] = None
    upload_to_chat: bool = True

    rename_col_map: dict[str, str] | SkipJsonSchema[None] = None

    table_header_format: dict = {
        "bg_color": "#966919",
        "bold": True,
        "font_color": "white",
        "text_wrap": True,
    }

    skip_ingestion: bool = True

    table_data_format: dict = {
        "bg_color": "#FFFFFF",
        "bold": False,
        "font_color": "black",
        "text_wrap": True,
        "border": 1,
        "valign": "top",
    }

    @model_validator(mode="after")
    def validate_upload_to_chat(self):
        if not self.upload_to_chat and not self.upload_scope_id:
            raise ValueError("Either upload_to_chat or upload_scope_id must be set")
        return self
