"""Template handler module."""

from pathlib import Path

from unique_toolkit._common.experimental.write_up_agent.services.template_handler.exceptions import (
    ColumnExtractionError,
    TemplateHandlerError,
    TemplateParsingError,
    TemplateRenderingError,
    TemplateStructureError,
)
from unique_toolkit._common.experimental.write_up_agent.services.template_handler.service import (
    TemplateHandler,
)
from unique_toolkit._common.experimental.write_up_agent.utils import template_loader


def default_jinja_template_loader():
    return template_loader(Path(__file__).parent, "default_template.j2")


__all__ = [
    "TemplateHandler",
    "TemplateHandlerError",
    "TemplateParsingError",
    "TemplateStructureError",
    "TemplateRenderingError",
    "ColumnExtractionError",
]
