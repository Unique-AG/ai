import logging
import re
from mimetypes import guess_type
from typing import override

from openai import AsyncOpenAI
from pydantic import BaseModel
from unique_sdk import Content

from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    ResponsesApiPostprocessor,
)
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

logger = logging.getLogger(__name__)


class DisplayCodeInterpreterFilesPostProcessorConfig(BaseModel):
    model_config = get_configuration_dict()
    upload_scope_id: str


class DisplayCodeInterpreterFilesPostProcessor(
    ResponsesApiPostprocessor,
):
    def __init__(
        self,
        client: AsyncOpenAI,
        content_service: ContentService,
        config: DisplayCodeInterpreterFilesPostProcessorConfig,
    ) -> None:
        super().__init__(self.__class__.__name__)
        self._content_service = content_service
        self._config = config
        self._client = client
        self._content_map = {}

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        logger.info("Fetching and adding code interpreter files to the response")

        container_files = loop_response.container_files
        logger.info("Found %s container files", len(container_files))

        self._content_map = {}
        for container_file in container_files:
            logger.info("Fetching file content for %s", container_file.filename)
            file_content = await self._client.containers.files.content.retrieve(
                container_id=container_file.container_id, file_id=container_file.file_id
            )

            logger.info(
                "Uploading file content for %s to knowledge base",
                container_file.filename,
            )
            content = self._content_service.upload_content_from_bytes(
                content=file_content.content,
                content_name=container_file.filename,
                skip_ingestion=True,
                mime_type=guess_type(container_file.filename)[0] or "text/plain",
                scope_id=self._config.upload_scope_id,
            )
            self._content_map[container_file.filename] = content

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        ref_number = _get_next_ref_number(loop_response.message.references)
        changed = False
        # images
        for filename, content in self._content_map.items():
            # Images
            loop_response.message.text, replaced = _replace_container_image_citation(
                text=loop_response.message.text, filename=filename, content=content
            )
            changed |= replaced

            # Files
            loop_response.message.text, replaced = _replace_container_file_citation(
                text=loop_response.message.text,
                filename=filename,
                ref_number=ref_number,
            )
            changed |= replaced
            if replaced:
                loop_response.message.references.append(
                    ContentReference(
                        sequence_number=ref_number,
                        source_id=content.id,
                        source="node-ingestion-chunks",
                        url=f"unique://content/{content.id}",
                        name=filename,
                    )
                )
                ref_number += 1
        return changed

    @override
    async def remove_from_text(self, text) -> str:
        return text


def _get_next_ref_number(references: list[ContentReference]) -> int:
    max_ref_number = 0
    for ref in references:
        max_ref_number = max(max_ref_number, ref.sequence_number)
    return max_ref_number + 1


def _replace_container_image_citation(
    text: str, filename: str, content: Content
) -> tuple[str, bool]:
    image_markdown = rf"!\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"

    if not re.search(image_markdown, text):
        logger.info("No image markdown found for %s", filename)
        return text, False

    logger.info("Displaying image %s", filename)
    return re.sub(
        image_markdown,
        f"![image](unique://content/{content.id})",
        text,
    ), True


def _replace_container_file_citation(
    text: str, filename: str, ref_number: int
) -> tuple[str, bool]:
    file_markdown = rf"\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"

    if not re.search(file_markdown, text):
        logger.info("No file markdown found for %s", filename)
        return text, False

    logger.info("Displaying file %s", filename)
    return re.sub(
        file_markdown,
        f"<sup>{ref_number}</sup>",
        text,
    ), True
