from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.docx_generator import DocxGeneratorConfig
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.utils import load_template

# Get the directory containing this file
_PROMPTS_DIR = Path(__file__).parent


REPORT_TEMPLATE: str = load_template(_PROMPTS_DIR, "report_template.j2")


class DocxRendererType(StrEnum):
    DOCX = "docx"
    CHAT = "chat"


class ReportRendererConfig(BaseModel):
    model_config = get_configuration_dict()

    report_template: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=len(REPORT_TEMPLATE.split("\n"))),
    ] = Field(
        default=REPORT_TEMPLATE,
        description="Jinja2 template for the report.",
    )

    renderer_type: DocxRendererType = Field(
        default=DocxRendererType.DOCX,
        description="The type of renderer to use.",
    )

    docx_renderer_config: DocxGeneratorConfig = Field(
        default_factory=DocxGeneratorConfig,
        description="The configuration for the DOCX renderer.",
    )
    ingest_docx_report: bool = Field(
        default=True,
        description="Whether to ingest the DOCX report into the chat.",
    )
