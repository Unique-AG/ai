import asyncio
import logging
import re
from mimetypes import guess_type
from typing import override

from openai import AsyncOpenAI
from openai.types.responses.response_output_text import AnnotationContainerFileCitation
from pydantic import BaseModel, Field

from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    ResponsesApiPostprocessor,
)
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.agentic.tools.utils import failsafe_async
from unique_toolkit.content.schemas import Content, ContentReference
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

logger = logging.getLogger(__name__)


class DisplayCodeInterpreterFilesPostProcessorConfig(BaseModel):
    model_config = get_configuration_dict()
    upload_scope_id: str

    file_download_failed_message: str = Field(
        default="⚠️ File download failed ...",
        description="The message to display when a file download fails.",
    )
    max_concurrent_file_downloads: int = Field(
        default=10,
        description="The maximum number of concurrent file downloads.",
    )


class DisplayCodeInterpreterFilesPostProcessor(
    ResponsesApiPostprocessor,
):
    def __init__(
        self,
        client: AsyncOpenAI,
        content_service: ContentService | KnowledgeBaseService,
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

        semaphore = asyncio.Semaphore(self._config.max_concurrent_file_downloads)
        tasks = [
            self._download_and_upload_container_file_to_knowledge_base(
                citation, semaphore
            )
            for citation in container_files
        ]
        results = await asyncio.gather(*tasks)

        for citation, result in zip(container_files, results):
            self._content_map[citation.filename] = result

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        ref_number = _get_next_ref_number(loop_response.message.references)
        changed = False

        for filename, content in self._content_map.items():
            if content is None:
                loop_response.message.text, replaced = _replace_container_file_error(
                    text=loop_response.message.text,
                    filename=filename,
                    error_message=self._config.file_download_failed_message,
                )
                changed |= replaced
                continue

            is_image = (guess_type(filename)[0] or "").startswith("image/")

            # Images
            if is_image:
                loop_response.message.text, replaced = (
                    _replace_container_image_citation(
                        text=loop_response.message.text,
                        filename=filename,
                        content=content,
                    )
                )
                changed |= replaced

            # Files
            else:
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

    @failsafe_async(failure_return_value=None, logger=logger)
    async def _download_and_upload_container_file_to_knowledge_base(
        self,
        container_file: AnnotationContainerFileCitation,
        semaphore: asyncio.Semaphore,
    ) -> Content | None:
        async with semaphore:
            logger.info("Fetching file content for %s", container_file.filename)
            file_content = await self._client.containers.files.content.retrieve(
                container_id=container_file.container_id, file_id=container_file.file_id
            )

            logger.info(
                "Uploading file content for %s to knowledge base",
                container_file.filename,
            )
            return await self._content_service.upload_content_from_bytes_async(
                content=file_content.content,
                content_name=container_file.filename,
                skip_ingestion=True,
                mime_type=guess_type(container_file.filename)[0] or "text/plain",
                scope_id=self._config.upload_scope_id,
            )


def _get_next_ref_number(references: list[ContentReference]) -> int:
    max_ref_number = 0
    for ref in references:
        max_ref_number = max(max_ref_number, ref.sequence_number)
    return max_ref_number + 1


def _replace_container_file_error(
    text: str, filename: str, error_message: str
) -> tuple[str, bool]:
    image_markdown = rf"!?\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"

    if not re.search(image_markdown, text):
        logger.info("No image markdown found for %s", filename)
        return text, False

    logger.info("Displaying image %s", filename)
    return re.sub(
        image_markdown,
        error_message,
        text,
    ), True


def _replace_container_image_citation(
    text: str, filename: str, content: Content
) -> tuple[str, bool]:
    image_markdown = rf"!?\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"

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
