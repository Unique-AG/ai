import io
import logging
import re
from pathlib import Path

from docxtpl import DocxTemplate
from markdown_it import MarkdownIt
from unique_sdk._unique_ql import UQLOperator

from unique_toolkit._common.docx_generator.config import DocxGeneratorConfig
from unique_toolkit._common.docx_generator.schemas import (
    ContentField,
    DocxGeneratorResult,
    HeadingField,
    ParagraphField,
    RunField,
    RunsField,
)
from unique_toolkit._common.utils.files import FileMimeType
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.service import ContentService

generator_dir_path = Path(__file__).resolve().parent

_CHAT_FILE_PREFIX_PATTERN = r"Chat_\d{4}-\d{2}-\d{2}_\d{2}:\d{2}_"

_LOGGER = logging.getLogger(__name__)


class DocxGeneratorService:
    def __init__(self, config: DocxGeneratorConfig, *, template: bytes | None = None):
        self._config = config
        self._template = template

    @staticmethod
    def parse_markdown_to_list_content_fields(
        markdown: str, offset_header_lvl: int = 0
    ) -> list[HeadingField | ParagraphField | RunsField]:
        # Initialize markdown-it parser
        md = MarkdownIt()

        tokens = md.parse(markdown)

        elements = []
        current_section = {}
        in_list = False
        bullet_list_indent_level = 0
        list_item_open = False

        for token in tokens:
            if token.type == "bullet_list_open":
                in_list = True
                bullet_list_indent_level = int(token.level / 2)

            elif token.type == "bullet_list_close":
                in_list = False
                bullet_list_indent_level = 0

            elif token.type == "list_item_open":
                if list_item_open:
                    elements.append(current_section)
                list_item_open = True
                list_level = token.level - bullet_list_indent_level
                current_section = {
                    "type": RunsField,
                    "runs": [],
                    "is_list_item": True,
                    "level": list_level,
                }

            elif token.type == "list_item_close":
                if current_section and current_section.get("runs"):
                    elements.append(current_section)
                current_section = {}
                list_item_open = False

            if token.type == "heading_open":
                # Heading start, token.tag gives the level (e.g., 'h1', 'h2', etc.)
                header_lvl = int(token.tag[1])  # Extract the level number from tag
                current_section = {
                    "type": HeadingField,
                    "text": "",
                    "level": header_lvl + offset_header_lvl,
                }

            elif token.type == "heading_close":
                if current_section:
                    elements.append(current_section)
                current_section = {}

            elif token.type == "paragraph_open":
                if not in_list:  # Only create new paragraph if not in a list
                    current_section = {"type": RunsField, "runs": []}

            elif token.type == "paragraph_close":
                if not in_list and current_section:  # Only append if not in a list
                    elements.append(current_section)
                    current_section = {}

            elif token.type == "inline":
                if current_section.get("type") == HeadingField:
                    content = token.content
                    if content.startswith("_page"):
                        # replace "_pageXXXX_" with "PageXXXX", where XXXX can be any characters and numbers
                        content = re.sub(
                            r"^_page([a-zA-Z0-9\s-]+)_(.*?)",
                            r"Page\1",
                            content,
                        )
                        bold = True
                    current_section["text"] += content
                elif "runs" in current_section:
                    bold = False
                    italic = False
                    runs = []
                    if token.children:
                        for child in token.children:
                            content = child.content
                            if child.type == "strong_open":
                                bold = True
                            elif child.type == "strong_close":
                                bold = False
                            elif child.type == "em_open":
                                italic = True
                            elif child.type == "em_close":
                                italic = False
                            if child.type == "softbreak":
                                content += "\n"
                            if content:  # Only add non-empty content
                                runs.append(
                                    RunField(
                                        text=content,
                                        bold=bold,
                                        italic=italic,
                                    )
                                )
                    else:
                        runs.append(
                            RunField(
                                text=token.content,
                                bold=bold,
                                italic=italic,
                            )
                        )

                    current_section["runs"].extend(runs)

        # Process remaining elements
        contents = []
        for element in elements:
            if not element:
                continue
            if element["type"] == HeadingField:
                contents.append(
                    HeadingField(
                        text=element["text"],
                        level=element["level"],
                    )
                )
            elif element["type"] == RunsField:
                if element.get("is_list_item", False):
                    level: int = min(element.get("level", 1), 5)
                    if level > 1:
                        style = "List Bullet " + str(level)
                    else:
                        style = "List Bullet"
                    contents.append(RunsField(style=style, runs=element["runs"]))
                else:
                    contents.append(RunsField(runs=element["runs"]))

        return contents

    def generate_from_template(
        self,
        subdoc_content: list[HeadingField | ParagraphField | RunsField],
        fields: dict | None = None,
    ) -> bytes | None:
        """
        Generate a docx file from a template with the given content.

        Args:
            subdoc_content: The content to be added to the docx file.
            fields: Other fields to be added to the docx file. Defaults to None.

        Returns:
            The generated docx file as bytes, or None on error.
        """
        doc = DocxTemplate(io.BytesIO(self.template))

        try:
            # Seed context with config template_fields (e.g. date, document_title)
            content = dict(self._config.template_fields)
            content["body"] = ContentField(contents=subdoc_content)

            if fields:
                content.update(fields)

            for key, value in content.items():
                if isinstance(value, ContentField):
                    content[key] = value.add(doc)

            doc.render(content)
            docx_rendered_object = io.BytesIO()

            doc.save(docx_rendered_object)
            docx_rendered_object.seek(0)

            return docx_rendered_object.getvalue()

        except Exception as e:
            _LOGGER.error(f"Error generating docx: {e}")
            return None

    def generate_from_template_with_result(
        self,
        subdoc_content: list[HeadingField | ParagraphField | RunsField],
        fields: dict | None = None,
    ) -> DocxGeneratorResult:
        """
        Generate a docx file and return a DocxGeneratorResult wrapper.

        This is a convenience method for callers that previously used the monorepo
        DocxGeneratorService which returned DocxGeneratorResult directly.

        Args:
            subdoc_content: The content to be added to the docx file.
            fields: Other fields to be added to the docx file. Defaults to None.

        Returns:
            DocxGeneratorResult with success flag and docx bytes.
        """
        result = self.generate_from_template(subdoc_content, fields)
        if result is not None:
            return DocxGeneratorResult(
                user_message="ℹ️ Template generated successfully!",
                docx_object=result,
                success=True,
            )
        return DocxGeneratorResult(
            user_message="❌ Error generating docx!",
            docx_object=None,
            success=False,
        )

    def upload_and_create_reference(
        self,
        *,
        docx_object: bytes,
        sequence_number: int,
        file_name: str,
        content_service: ContentService,
        chat_service: ChatService,
    ) -> ContentReference | None:
        """
        Upload a generated DOCX and create a ContentReference for use in chat.

        Uploads to chat if config.upload_to_chat is True, and additionally to
        a scope if config.upload_scope_id is set. At least one must be configured.

        Args:
            docx_object: The generated DOCX bytes to upload.
            sequence_number: The sequence number for the ContentReference.
            file_name: The original file name (chat prefix will be stripped).
            content_service: The ContentService to use for uploading.
            chat_service: The ChatService used to obtain chat_id and message_id.

        Returns:
            A ContentReference, or None if an error occurs.
        """
        try:
            mime_type = FileMimeType.DOCX.value

            content_name = (
                re.sub(_CHAT_FILE_PREFIX_PATTERN, "", Path(file_name).stem)
                + self._config.upload_suffix
            )

            content_id: str | None = None

            if self._config.upload_to_chat:
                created = content_service.upload_content_from_bytes(
                    content=docx_object,
                    content_name=content_name,
                    chat_id=chat_service.chat_id,
                    mime_type=mime_type,
                    skip_ingestion=self._config.skip_ingestion,
                )
                content_id = created.id

            if self._config.upload_scope_id:
                created = content_service.upload_content_from_bytes(
                    content=docx_object,
                    content_name=content_name,
                    scope_id=self._config.upload_scope_id,
                    mime_type=mime_type,
                    skip_ingestion=self._config.skip_ingestion,
                )
                content_id = created.id

            if content_id is None:
                raise ValueError(
                    "No upload destination configured: set upload_to_chat=True or upload_scope_id."
                )

            return ContentReference(
                id=content_id,
                sequence_number=sequence_number,
                message_id=chat_service.assistant_message_id,
                name=content_name,
                source=content_name,
                source_id=content_id,
                url=f"unique://content/{content_id}",
            )

        except Exception as e:
            _LOGGER.error(f"Error uploading content: {e}")
            return None

    @staticmethod
    def resolve_template(
        config: DocxGeneratorConfig,
        content_service: ContentService,
    ) -> bytes | None:
        """
        Fetch template bytes using config's template_content_id or
        template_name + template_scope_id.

        Returns None if neither is set (the service will fall back to the
        default bundled template automatically).

        Args:
            config: The DocxGeneratorConfig with template resolution settings.
            content_service: The ContentService to use for downloading.

        Returns:
            Template bytes, or None to use the default template.
        """
        try:
            if config.template_content_id:
                return DocxGeneratorService._fetch_template_by_content_id(
                    config.template_content_id, content_service
                )
            elif config.template_name and config.template_scope_id:
                return DocxGeneratorService._fetch_template_by_name(
                    config.template_name, config.template_scope_id, content_service
                )
        except Exception as e:
            _LOGGER.exception(f"Error resolving template, falling back to default: {e}")

        return None

    @staticmethod
    def _fetch_template_by_content_id(
        content_id: str, content_service: ContentService
    ) -> bytes:
        response = content_service.request_content_by_id(content_id)
        if response.status_code != 200:
            raise ValueError(
                f"Failed to download template from content ID: {content_id}"
            )
        _LOGGER.info(f"Template downloaded from content ID: {content_id}")
        return response.content

    @staticmethod
    def _fetch_template_by_name(
        template_name: str,
        template_scope_id: str,
        content_service: ContentService,
    ) -> bytes:
        where_clause: dict = {
            "OR": [
                {
                    "title": {UQLOperator.EQUALS: template_name},
                    "ownerId": {UQLOperator.EQUALS: template_scope_id},
                },
                {
                    "key": {UQLOperator.EQUALS: template_name},
                    "ownerId": {UQLOperator.EQUALS: template_scope_id},
                },
            ]
        }

        contents = content_service.search_contents(where=where_clause)
        if len(contents) == 0:
            raise ValueError(
                f"No template found with the name `{template_name}` in knowledge base."
            )
        if len(contents) > 1:
            raise ValueError(
                f"Multiple templates found with the name `{template_name}` in knowledge base."
            )

        result = DocxGeneratorService._fetch_template_by_content_id(
            contents[0].id, content_service
        )
        _LOGGER.info(f"Template downloaded from template name: {template_name}")
        return result

    def _get_default_template(self) -> bytes:
        generator_dir_path = Path(__file__).resolve().parent
        path = generator_dir_path / "template" / "Doc Template.docx"

        file_content = path.read_bytes()

        _LOGGER.info("Template downloaded from default template")

        return file_content

    @property
    def template(self) -> bytes:
        return self._template or self._get_default_template()
