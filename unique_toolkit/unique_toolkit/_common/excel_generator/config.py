from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class ExcelGeneratorConfig(BaseModel):
    model_config = get_configuration_dict()

    upload_suffix: str = Field(
        default="_answers.xlsx",
        description="The suffix appended to the output file name.",
    )
    rename_col_map: dict[str, str] | None = Field(
        default=None,
        description="A dictionary for renaming DataFrame columns before writing.",
    )
    table_header_format: dict = Field(
        default={
            "bg_color": "#966919",
            "bold": True,
            "font_color": "white",
            "text_wrap": True,
        },
        description="xlsxwriter format dict applied to header cells.",
    )
    table_data_format: dict = Field(
        default={
            "bg_color": "#FFFFFF",
            "bold": False,
            "font_color": "black",
            "text_wrap": True,
            "border": 1,
            "valign": "top",
        },
        description="xlsxwriter format dict applied to data cells.",
    )
