import asyncio
import logging
import re
from mimetypes import guess_type
from typing import NamedTuple, override

from openai import AsyncOpenAI
from openai.types.responses.response_output_text import AnnotationContainerFileCitation
from pydantic import BaseModel, Field, RootModel
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit import ChatService
from unique_toolkit._common.execution import failsafe_async
from unique_toolkit.agentic.feature_flags.feature_flags import feature_flags
from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    ResponsesApiPostprocessor,
)
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.schemas import (
    CodeInterpreterBlock,
    CodeInterpreterFile,
    CodeInterpreterFileType,
    ResponsesLanguageModelStreamResponse,
)
from unique_toolkit.services.knowledge_base import KnowledgeBaseService
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

logger = logging.getLogger(__name__)


class DisplayCodeInterpreterFilesPostProcessorConfig(BaseModel):
    model_config = get_configuration_dict()
    upload_to_chat: SkipJsonSchema[bool] = Field(
        default=True,
        description="Whether to upload the generated files to the chat.",
    )
    upload_scope_id: SkipJsonSchema[str] = Field(
        default="<SCOPE_ID_PLACEHOLDER>",
        description="The scope ID where the generated files will be uploaded. Ignored if `uploadToChat` is set.",
    )

    file_download_failed_message: str = Field(
        default="⚠️ File download failed ...",
        description="The message to display when a file download fails.",
    )
    max_concurrent_file_downloads: int = Field(
        default=10,
        description="The maximum number of concurrent file downloads.",
    )


class _ContentInfo(NamedTuple):
    filename: str
    content_id: str


_SHORT_TERM_MEMORY_KEY = "code_interpreter_files"
_DisplayedFilesShortTermMemorySchema = RootModel[list[_ContentInfo]]


def _init_short_term_memory_manager(
    company_id: str, user_id: str, chat_id: str
) -> PersistentShortMemoryManager[_DisplayedFilesShortTermMemorySchema]:
    short_term_memory_service = ShortTermMemoryService(
        company_id=company_id,
        user_id=user_id,
        chat_id=chat_id,
        message_id=None,
    )
    return PersistentShortMemoryManager(
        short_term_memory_service=short_term_memory_service,
        short_term_memory_schema=_DisplayedFilesShortTermMemorySchema,
        short_term_memory_name=_SHORT_TERM_MEMORY_KEY,
    )


class DisplayCodeInterpreterFilesPostProcessor(
    ResponsesApiPostprocessor,
):
    def __init__(
        self,
        client: AsyncOpenAI,
        content_service: ContentService | KnowledgeBaseService,
        config: DisplayCodeInterpreterFilesPostProcessorConfig,
        chat_service: ChatService | None = None,
        # Short term memory arguments, we prefer to explicitely pass the required auth variables
        # as it is crucial that we use chat-level short term memory not to leak user files to other chats.
        # Technically, short term memory can be scoped company-level, we would like to ensure this case is avoided.
        company_id: str | None = None,
        user_id: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        super().__init__(self.__class__.__name__)

        self._content_service = content_service
        self._chat_service = chat_service
        self._client = client
        self._config = config
        self._company_id = company_id

        if self._chat_service is None:
            raise ValueError("ChatService is required if uploadToChat is True")

        self._short_term_memory_manager = None
        if chat_id is not None and user_id is not None and company_id is not None:
            self._short_term_memory_manager = _init_short_term_memory_manager(
                company_id=company_id,
                user_id=user_id,
                chat_id=chat_id,
            )

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        logger.info("Fetching and adding code interpreter files to the response")

        container_files = loop_response.container_files
        logger.info("Found %s container files", len(container_files))

        self._content_map: dict[str, str | None] = await self._load_previous_files()  # type: ignore

        semaphore = asyncio.Semaphore(self._config.max_concurrent_file_downloads)
        tasks = [
            self._download_and_upload_container_files_to_knowledge_base(
                citation, semaphore
            )
            for citation in container_files
        ]
        results = await asyncio.gather(*tasks)

        for citation, result in zip(container_files, results):
            # Overwrite if file has been re-generated
            self._content_map[citation.filename] = (
                result.content_id if result is not None else None
            )

        await self._save_generated_files(
            [
                _ContentInfo(filename=filename, content_id=content_id)
                for filename, content_id in self._content_map.items()
                if content_id is not None
            ]
        )

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        ref_number = _get_next_ref_number(loop_response.message.references)
        changed = False

        for filename, content_id in self._content_map.items():
            if content_id is None:
                loop_response.message.text, replaced = _replace_container_file_error(
                    text=loop_response.message.text,
                    filename=filename,
                    error_message=self._config.file_download_failed_message,
                )
                changed |= replaced
                continue

            is_image = (guess_type(filename)[0] or "").startswith("image/")
            is_html = (guess_type(filename)[0] or "") == "text/html"

            # Images
            if is_image:
                loop_response.message.text, replaced = (
                    _replace_container_image_citation(
                        text=loop_response.message.text,
                        filename=filename,
                        content_id=content_id,
                    )
                )
                changed |= replaced

            # HTML (behind feature flag)
            elif is_html and feature_flags.enable_html_rendering_un_15131.is_enabled(
                self._company_id
            ):
                loop_response.message.text, replaced = _replace_container_html_citation(
                    text=loop_response.message.text,
                    filename=filename,
                    content_id=content_id,
                )
                changed |= replaced

            # Files (including HTML when feature flag is disabled)
            else:
                loop_response.message.text, replaced = _replace_container_file_citation(
                    text=loop_response.message.text,
                    filename=filename,
                    content_id=content_id,
                )
                changed |= replaced

            is_html_rendered = (
                is_html
                and feature_flags.enable_html_rendering_un_15131.is_enabled(
                    self._company_id
                )
            )
            if replaced and not is_image and not is_html_rendered:
                loop_response.message.references.append(
                    ContentReference(
                        sequence_number=ref_number,
                        source_id=content_id,
                        source="node-ingestion-chunks",
                        url=f"unique://content/{content_id}",
                        name=filename,
                    )
                )
                ref_number += 1

        if feature_flags.enable_code_execution_fence_un_17972.is_enabled(
            self._company_id
        ):
            code_blocks = _build_code_blocks(loop_response, self._content_map)
            text_before = loop_response.message.text
            loop_response.message.text = _inject_code_execution_fences(
                loop_response.message.text,
                code_blocks,
            )
            changed |= loop_response.message.text != text_before

        return changed

    @override
    async def remove_from_text(self, text) -> str:
        return text

    @failsafe_async(failure_return_value=None, logger=logger)
    async def _download_and_upload_container_files_to_knowledge_base(
        self,
        container_file: AnnotationContainerFileCitation,
        semaphore: asyncio.Semaphore,
    ) -> _ContentInfo | None:
        async with semaphore:
            logger.info("Fetching file content for %s", container_file.filename)
            file_content = await self._client.containers.files.content.retrieve(
                container_id=container_file.container_id, file_id=container_file.file_id
            )

            logger.info(
                "Uploading file content for %s to knowledge base",
                container_file.filename,
            )

            assert self._chat_service is not None  # Checked in __init__
            content = await self._chat_service.upload_to_chat_from_bytes_async(
                content=file_content.content,
                content_name=container_file.filename,
                mime_type=guess_type(container_file.filename)[0] or "text/plain",
                skip_ingestion=True,
                hide_in_chat=True,
            )

            return _ContentInfo(filename=container_file.filename, content_id=content.id)

    async def _load_previous_files(self) -> dict[str, str]:
        if self._short_term_memory_manager is None:
            return {}

        logger.info(
            "Loading previously generated code interpreter files from short term memory"
        )
        memory = await self._short_term_memory_manager.load_async()

        if memory is None:
            logger.info(
                "No previously generated code interpreter files found in short term memory"
            )
            return {}

        logger.info(
            "Found %s previously generated code interpreter files", len(memory.root)
        )

        return {content.filename: content.content_id for content in memory.root}

    async def _save_generated_files(self, content_infos: list[_ContentInfo]) -> None:
        if self._short_term_memory_manager is None or len(content_infos) == 0:
            return

        await self._short_term_memory_manager.save_async(
            _DisplayedFilesShortTermMemorySchema(root=content_infos)
        )


def _get_file_type(filename: str) -> CodeInterpreterFileType:
    mime = guess_type(filename)[0] or ""
    if mime.startswith("image/"):
        return "image"
    if mime == "text/html":
        return "html"
    return "document"


def _to_frontend_type(file_type: CodeInterpreterFileType) -> str:
    """Map our CodeInterpreterFileType to the type token the frontend parser expects."""
    if file_type == "image":
        return "chart"
    if file_type == "html":
        return "html"
    return "document"


def _build_code_execution_fence(block: CodeInterpreterBlock) -> str:
    """Build a codeExecution fence for one code block.

    Uses 4 backticks for the outer fence so the inner 3-backtick code fence does
    not prematurely close it (CommonMark rule: closing fence must match opening
    backtick count).

    The format matches what parseCodeExecutionData / parseContentIdLines expect:
      - <summary> tag  → title
      - inner ```python fence → sourceCode + language
      - lines after the inner closing ``` → outputRefs (content_id + type)
    """
    outer = "````"
    inner = "```"
    content_id_lines = "\n".join(
        f"unique://content/{f.content_id} {_to_frontend_type(f.type)}"
        for f in block.files
    )
    return (
        f"{outer}codeExecution\n"
        f"<summary>Code Interpreter Call</summary>\n"
        f"{inner}python\n"
        f"{block.code.rstrip()}\n"
        f"{inner}\n"
        f"{content_id_lines}\n"
        f"{outer}"
    )


def _inline_ref_pattern(file: CodeInterpreterFile) -> re.Pattern[str]:
    """Return a compiled pattern matching the inline ref for a file in message text.

    After apply_postprocessing_to_response replaces sandbox paths, each file type
    has a distinct inline form in the text:
      image    → ![image](unique://content/{content_id})
      document → [{filename}](unique://content/{content_id})
      html     → ```HtmlRendering\\n100%\\n500px\\n\\nunique://content/{content_id}\\n\\n```
    """
    cid = re.escape(file.content_id)
    fname = re.escape(file.filename)
    if file.type == "image":
        return re.compile(rf"!\[image\]\(unique://content/{cid}\)")
    if file.type == "html":
        return re.compile(
            rf"```HtmlRendering\n100%\n500px\n\nunique://content/{cid}\n\n```",
            re.DOTALL,
        )
    return re.compile(rf"\[{fname}\]\(unique://content/{cid}\)")


_DETAILS_CODE_BLOCK_RE = re.compile(
    r"\n*<details><summary>Code Interpreter Call</summary>.*?</details>\n*",
    re.DOTALL,
)


def _inject_code_execution_fences(
    text: str, code_blocks: list[CodeInterpreterBlock]
) -> str:
    """Replace inline file refs in text with codeExecution fences.

    For each code block, finds the first inline ref belonging to that block and
    replaces it with the fence. Remaining inline refs for the same block are
    removed (the files are now represented inside the fence).

    After all blocks are processed, any <details> blocks emitted by
    ShowExecutedCodePostprocessor are stripped — they are superseded by the fences.
    """
    for block in code_blocks:
        if not block.files:
            continue
        fence = _build_code_execution_fence(block)
        fence_placed = False
        for file in block.files:
            pattern = _inline_ref_pattern(file)
            if not fence_placed:
                new_text, n = re.subn(pattern, lambda m, _f=fence: _f, text, count=1)
                if n:
                    text = new_text
                    fence_placed = True
            # Remove all remaining occurrences of this file's inline ref. This covers:
            # - multi-file blocks where subsequent files' refs follow the fence position
            # - overwrite cases where the model emitted two download links for the same file
            if fence_placed:
                text = re.sub(pattern, "", text)
    return _DETAILS_CODE_BLOCK_RE.sub("", text)


def _build_code_blocks(
    loop_response: ResponsesLanguageModelStreamResponse,
    content_map: dict[str, str | None],
) -> list[CodeInterpreterBlock]:
    """Map each code interpreter call to the files it produced via /mnt/data/ path matching.

    For each file, the LAST code block that references its path is treated as the
    producer — this handles the case where a file is overwritten across blocks, where
    the final content belongs to the last writer.
    """
    calls = loop_response.code_interpreter_calls

    # Step 1: for each file, find the index of the last block that references it.
    file_to_block_idx: dict[str, int] = {}
    for idx, call in enumerate(calls):
        if not call.code:
            continue
        for annotation in loop_response.container_files:
            if (
                content_map.get(annotation.filename) is not None
                and f"/mnt/data/{annotation.filename}" in call.code
            ):
                file_to_block_idx[annotation.filename] = idx

    # Step 2: group files by their owning block index, deduplicating by filename.
    # OpenAI may emit multiple annotations for the same filename when a file is
    # overwritten across executions. Using a dict keyed by filename ensures each
    # file appears exactly once per block (last annotation wins, consistent with
    # the last-writer-wins rule applied in step 1).
    block_file_map: dict[int, dict[str, CodeInterpreterFile]] = {}
    for annotation in loop_response.container_files:
        content_id = content_map.get(annotation.filename)
        if content_id is None:
            continue
        idx = file_to_block_idx.get(annotation.filename)
        if idx is None:
            continue
        block_file_map.setdefault(idx, {})[annotation.filename] = CodeInterpreterFile(
            filename=annotation.filename,
            content_id=content_id,
            type=_get_file_type(annotation.filename),
        )

    # Step 3: build result preserving block execution order.
    return [
        CodeInterpreterBlock(code=calls[idx].code, files=list(files.values()))
        for idx, files in sorted(block_file_map.items())
        if calls[idx].code
    ]


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
    text: str, filename: str, content_id: str
) -> tuple[str, bool]:
    image_markdown = rf"!?\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"

    if not re.search(image_markdown, text):
        logger.info("No image markdown found for %s", filename)
        return text, False

    logger.info("Displaying image %s", filename)
    return re.sub(
        image_markdown,
        f"![image](unique://content/{content_id})",
        text,
    ), True


def _replace_container_html_citation(
    text: str, filename: str, content_id: str
) -> tuple[str, bool]:
    html_markdown = rf"!?\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"

    if not re.search(html_markdown, text):
        logger.info("No HTML markdown found for %s", filename)
        return text, False

    logger.info("Displaying HTML %s", filename)
    html_rendering_block = f"""```HtmlRendering
100%
500px

unique://content/{content_id}

```"""
    return re.sub(
        html_markdown,
        html_rendering_block,
        text,
    ), True


def _replace_container_file_citation(
    text: str, filename: str, content_id: str
) -> tuple[str, bool]:
    file_markdown = rf"\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"

    if not re.search(file_markdown, text):
        logger.info("No file markdown found for %s", filename)
        return text, False

    logger.info("Displaying file %s", filename)
    return re.sub(
        file_markdown,
        f"[{filename}](unique://content/{content_id})",
        text,
    ), True
