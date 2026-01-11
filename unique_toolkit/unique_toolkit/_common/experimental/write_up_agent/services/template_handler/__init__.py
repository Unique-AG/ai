"""Template handler module."""

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


def default_jinja_template_loader() -> str:
    from pathlib import Path

    """Load the default Jinja template from file."""
    template_path = Path(__file__).parent / "default_template.j2"
    return template_path.read_text()


__all__ = [
    "default_jinja_template_loader",
    "TemplateHandler",
    "TemplateHandlerError",
    "TemplateParsingError",
    "TemplateStructureError",
    "TemplateRenderingError",
    "ColumnExtractionError",
]
