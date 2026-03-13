import asyncio
import json
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
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    strip_executed_code_blocks,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.schemas import (
    CodeInterpreterBlock,
    CodeInterpreterFile,
    CodeInterpreterFileType,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse
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
            _warn_unmatched_code_blocks(self._content_map, code_blocks)
            text_before = loop_response.message.text
            loop_response.message.text = _inject_code_execution_fences(
                loop_response.message.text,
                code_blocks,
            )
            changed |= loop_response.message.text != text_before

        _warn_missing_content_ids(loop_response.message.text, self._content_map)
        loop_response.message.text, dangling_replaced = _replace_dangling_sandbox_links(
            loop_response.message.text, self._config.file_download_failed_message
        )
        changed |= dangling_replaced

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


def _file_title(filename: str) -> str:
    """Derive a human-readable title from a filename.

    Strips the extension, replaces underscores and hyphens with spaces, and
    applies title case. e.g. monthly_revenue_chart.png -> Monthly Revenue Chart.
    """
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return stem.replace("_", " ").replace("-", " ").title()


def _file_frontend_type(filename: str) -> str:
    """Map filename to the type token the frontend expects in fileWithSource.

    Assumed enum (to be confirmed with frontend):
      excel   → .xlsx / .xls
      csv     → .csv
      word    → .docx / .doc
      pdf     → .pdf
      html    → .html / .htm
      image   → image/* MIME
      document → fallback
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = guess_type(filename)[0] or ""
    if mime.startswith("image/"):
        return "image"
    mapping = {
        "xlsx": "excel",
        "xls": "excel",
        "csv": "csv",
        "docx": "word",
        "doc": "word",
        "pdf": "pdf",
        "html": "html",
        "htm": "html",
    }
    return mapping.get(ext, "document")


def _escape_code_attr(code: str) -> str:
    """Escape the code string for embedding as a double-quoted attribute value.

    Uses JSON encoding so all special characters (quotes, backslashes, newlines,
    control chars) are handled consistently and safely.
    """
    return json.dumps(code.rstrip())[1:-1]


def _build_file_fence(file: CodeInterpreterFile, code: str, fence_id: int) -> str:
    """Build a per-file fence marker.

    Images produce an imgWithSource fence; all other types produce a
    fileWithSource fence. Each fence is self-contained: it carries the
    content_id, a title derived from the filename, the type, and the
    escaped source code.

    Format (4 backticks so inner code backticks never close the fence):
      ````imgWithSource(id='{n}', contentId='{id}', title="{title}", code="{escaped_code}")````
      ````fileWithSource(id='{n}', contentId='{id}', title="{title}", type="{type}", code="{escaped_code}")````
    """
    title = _file_title(file.filename)
    escaped = _escape_code_attr(code)
    outer = "````"
    if file.type == "image":
        tag = f"imgWithSource(id='{fence_id}', contentId='{file.content_id}', title=\"{title}\", code=\"{escaped}\")"
    else:
        ftype = _file_frontend_type(file.filename)
        tag = f'fileWithSource(id=\'{fence_id}\', contentId=\'{file.content_id}\', title="{title}", type="{ftype}", code="{escaped}")'
    return f"{outer}{tag}{outer}"


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


_FENCE_BLOCK_START = re.compile(
    r"^[^\n`]+?(````(?:imgWithSource|fileWithSource)\()",
    re.MULTILINE,
)

# Matches two consecutive fence blocks and normalises the gap between them to
# exactly one newline.  Two cases are handled:
#   - same line: any non-newline, non-backtick content (e.g. " and ", ", ")
#   - cross-line: 1 or 2 newlines optionally surrounded by horizontal whitespace
#     (list-item linebreak, or blank-line paragraph gap)
_CONSECUTIVE_FENCES_RE = re.compile(
    r"(````(?:imgWithSource|fileWithSource)\([^\n]*\)````)"
    r"(?:[^\n`]*|[ \t]*\n{1,2}[ \t]*)"
    r"(?=````(?:imgWithSource|fileWithSource)\()"
)


def _ensure_fences_are_standalone(text: str) -> str:
    """Strip any prefix text on the same line as a fence block.

    The LLM sometimes puts file references inside list items or labels, e.g.:
        - File: ````fileWithSource(...)````
    After fence injection the label is left over. Strip it so the frontend
    always receives the fence at the start of its own line, which is required
    for correct parsing by the markdown renderer.

    Only the prefix is removed; any trailing content after the closing `````
    is preserved (it's unusual but not harmful).
    """
    return _FENCE_BLOCK_START.sub(r"\1", text)


def _inject_code_execution_fences(
    text: str, code_blocks: list[CodeInterpreterBlock]
) -> str:
    """Replace inline file refs with imgWithSource / fileWithSource fences.

    Images get an imgWithSource fence; all other files (PDF, Excel, Word, CSV, etc.)
    get a fileWithSource fence. Both carry contentId, title, type (fileWithSource only),
    and the generating code so the frontend can render or offer a download with full
    context.

    Each file gets its own fence placed at the position of its inline ref. Duplicate
    refs for the same file (overwrite case) are removed after the first is replaced.
    When at least one fence was injected, executed-code <details> blocks are
    stripped via strip_executed_code_blocks() from the code_display postprocessor.

    fence_id is a message-level counter so each fence has a unique id.
    """
    fence_id = 1
    any_fence_injected = False
    for block in code_blocks:
        for file in block.files:
            fence = _build_file_fence(file, block.code, fence_id)
            pattern = _inline_ref_pattern(file)
            new_text, n = re.subn(pattern, lambda m, _f=fence: _f, text, count=1)
            if n:
                text = new_text
                fence_id += 1
                any_fence_injected = True
            else:
                logger.warning(
                    "Fence injection skipped: no inline ref matched for '%s' "
                    "(content_id=%s); fence discarded. "
                    "The file was uploaded but will not appear in the message.",
                    file.filename,
                    file.content_id,
                )
            # Remove duplicate refs (overwrite case)
            text = re.sub(pattern, "", text)
    if any_fence_injected:
        text = strip_executed_code_blocks(text)
        text = _ensure_fences_are_standalone(text)
        text = _CONSECUTIVE_FENCES_RE.sub(r"\1\n", text)
    return text


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
    result: list[CodeInterpreterBlock] = []
    for idx, files in sorted(block_file_map.items()):
        code = calls[idx].code
        if code:
            result.append(CodeInterpreterBlock(code=code, files=list(files.values())))
    return result


def _warn_missing_content_ids(text: str, content_map: dict[str, str | None]) -> None:
    """End-of-pipeline validation: warn for any uploaded file whose content_id is absent from text.

    After all postprocessing stages have run every successfully uploaded file should
    have its content_id referenced somewhere in the message text (either as a
    unique://content/<id> link or embedded in a fence attribute).  A missing content_id
    means the file was uploaded but the user will never see it.
    """
    for filename, content_id in content_map.items():
        if content_id is None:
            continue
        if content_id not in text:
            logger.info(
                "End-of-pipeline check: content_id '%s' for file '%s' is not present "
                "in the final message text — the file was uploaded but will not be "
                "visible to the user.",
                content_id,
                filename,
            )


# Matches the full markdown link (including optional leading !) wrapping a sandbox URL,
# so the entire `[label](sandbox://...)` token can be replaced rather than just the URL.
_SANDBOX_MARKDOWN_LINK_RE = re.compile(r"!?\[.*?\]\(sandbox:/mnt/data/\S+?\)")


def _replace_dangling_sandbox_links(text: str, error_message: str) -> tuple[str, bool]:
    """Replace any remaining sandbox:/mnt/data/ markdown links with an error message.

    A dangling link means either the LLM hallucinated a file reference (the sandbox
    link appears in the text but no matching container file annotation was emitted by
    OpenAI), or the link format did not match the expected regex in stage-1.  In both
    cases the user would see a broken link; this function replaces each such link with
    the configured error message and logs a warning so the incident is visible in logs.
    """
    matches = _SANDBOX_MARKDOWN_LINK_RE.findall(text)
    if not matches:
        return text, False
    for match in matches:
        logger.warning(
            "Dangling sandbox link found in final text: '%s'. "
            "The file was either never uploaded or the link format did not match "
            "the expected pattern — replacing with error message.",
            match,
        )
    return _SANDBOX_MARKDOWN_LINK_RE.sub(error_message, text), True


def _warn_unmatched_code_blocks(
    content_map: dict[str, str | None],
    code_blocks: list[CodeInterpreterBlock],
) -> None:
    """Warn for files that were uploaded but could not be matched to any code block.

    When the fence feature flag is on, every uploaded file should map to a code block
    via its /mnt/data/<filename> path so it can receive a fence.  If a file is not
    matched (e.g. the LLM used a variable for the output path rather than a literal
    string) it falls back to a plain unique://content/ link with no code context.
    The user can still download it, but the frontend artifact UI will not be shown.
    """
    fenced_filenames = {f.filename for block in code_blocks for f in block.files}
    for filename, content_id in content_map.items():
        if content_id is None:
            continue
        if filename not in fenced_filenames:
            logger.warning(
                "File '%s' (content_id=%s) could not be matched to any code block "
                "(literal path '/mnt/data/%s' not found in executed code). "
                "It will appear as a plain download link without code context — "
                "consider re-running the query if the artifact UI is expected.",
                filename,
                content_id,
                filename,
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
        logger.warning(
            "No sandbox link found for '%s'; file was uploaded but the LLM did not "
            "reference it — it will not be displayed.",
            filename,
        )
        return text, False

    logger.info("Replacing failed download for '%s' with error message", filename)
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
        logger.warning(
            "No sandbox link found for image '%s' (content_id=%s); "
            "file was uploaded but the LLM did not reference it — it will not be displayed.",
            filename,
            content_id,
        )
        return text, False

    logger.info("Inserting image citation for '%s'", filename)
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
        logger.warning(
            "No sandbox link found for HTML file '%s' (content_id=%s); "
            "file was uploaded but the LLM did not reference it — it will not be displayed.",
            filename,
            content_id,
        )
        return text, False

    logger.info("Inserting HTML rendering block for '%s'", filename)
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
        logger.warning(
            "No sandbox link found for file '%s' (content_id=%s); "
            "file was uploaded but the LLM did not reference it — it will not be displayed.",
            filename,
            content_id,
        )
        return text, False

    logger.info("Inserting file citation for '%s'", filename)
    return re.sub(
        file_markdown,
        f"[{filename}](unique://content/{content_id})",
        text,
    ), True
