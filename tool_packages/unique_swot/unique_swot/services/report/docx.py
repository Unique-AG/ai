from logging import getLogger

from unique_toolkit._common.docx_generator import (
    DocxGeneratorService,
)

_LOGGER = getLogger(__name__)


def convert_markdown_to_docx(
    markdown_content: str,
    docx_generator_service: DocxGeneratorService,
    fields: dict[str, str],
) -> bytes | None:
    docx_elements = docx_generator_service.parse_markdown_to_list_content_fields(
        markdown_content
    )
    return docx_generator_service.generate_from_template(docx_elements, fields)
