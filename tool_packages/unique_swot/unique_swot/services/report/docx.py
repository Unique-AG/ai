from logging import getLogger
from pathlib import Path

from jinja2 import Template
from unique_toolkit._common.docx_generator import (
    DocxGeneratorService,
)

from unique_swot.utils import load_template

CITATION_FOOTER_TEMPLATE: str = load_template(
    Path(__file__).parent, "citation_footer.j2"
)

_LOGGER = getLogger(__name__)


def add_citation_footer(markdown_report: str, citations: list[str]) -> str:
    return markdown_report + Template(CITATION_FOOTER_TEMPLATE).render(
        citations=citations
    )


def convert_markdown_to_docx(
    markdown_content: str,
    docx_generator_service: DocxGeneratorService,
    fields: dict[str, str],
) -> bytes | None:
    docx_elements = docx_generator_service.parse_markdown_to_list_content_fields(
        markdown_content
    )
    return docx_generator_service.generate_from_template(docx_elements, fields)
