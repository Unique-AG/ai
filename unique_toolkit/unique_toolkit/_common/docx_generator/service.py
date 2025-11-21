import io
import logging
import re
from pathlib import Path

from docxtpl import DocxTemplate
from markdown_it import MarkdownIt

from unique_toolkit._common.docx_generator.config import DocxGeneratorConfig
from unique_toolkit._common.docx_generator.schemas import (
    ContentField,
    HeadingField,
    ParagraphField,
    RunField,
    RunsField,
)

generator_dir_path = Path(__file__).resolve().parent


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

        # Preprocess markdown.
        # - Replace all headings with the correct heading level
        # - Remove "Relevant sources" heading
        # - Replace "# Proposed answer" with "#### Proposed answer"
        markdown = re.sub(r"(?m)^\s*## ", "#### ", markdown)
        markdown = re.sub(r"(?m)^\s*### ", "##### ", markdown)
        markdown = markdown.replace("# Relevant sources", "")
        markdown = markdown.replace("# Proposed answer", "#### Proposed answer")

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
    ):
        """
        Generate a docx file from a template with the given content.

        Args:
            subdoc_content (list[HeadingField | ParagraphField | RunsField]): The content to be added to the docx file.
            fields (dict): Other fields to be added to the docx file. Defaults to None.
        """
        doc = DocxTemplate(io.BytesIO(self.template))

        try:
            content = {}
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

    def _get_default_template(self) -> bytes:
        generator_dir_path = Path(__file__).resolve().parent
        path = generator_dir_path / "template" / "Doc Template.docx"

        file_content = path.read_bytes()

        _LOGGER.info("Template downloaded from default template")

        return file_content

    @property
    def template(self) -> bytes:
        return self._template or self._get_default_template()
