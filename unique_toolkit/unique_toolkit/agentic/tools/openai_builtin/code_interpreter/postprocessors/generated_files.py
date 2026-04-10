import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from mimetypes import guess_type
from typing import NamedTuple, override

import httpx
from openai import AsyncOpenAI
from openai.types.responses.response_output_text import AnnotationContainerFileCitation
from pydantic import BaseModel, Field, RootModel
from pydantic.json_schema import SkipJsonSchema
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    stop_after_attempt,
    wait_exponential,
)

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


class _ChatLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """LoggerAdapter that prefixes every message with ``[chat_id=…]``."""

    def process(self, msg: str, kwargs):  # type: ignore[override]
        extra = dict(self.extra) if self.extra else {}  # type: ignore[arg-type]
        return f"[chat_id={extra.get('chat_id', 'n/a')}] {msg}", kwargs


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
        default="⚠️ File could not be generated. Please try again.",
        description="The message to display when a file download fails after all retry attempts.",
    )
    max_concurrent_file_downloads: int = Field(
        default=10,
        description="The maximum number of concurrent file downloads.",
    )
    max_download_retries: int = Field(
        default=2,
        description="Maximum number of additional download attempts per container file after the first try (0 = no retries).",
    )
    download_retry_base_delay: float = Field(
        default=0.5,
        description="Base delay in seconds for exponential backoff between download/upload retries.",
    )
    progress_update_interval: float = Field(
        default=3.0,
        description="Minimum seconds between progress message updates sent to the user.",
    )
    download_chunk_size: int = Field(
        default=8192,
        description="Chunk size in bytes for streaming container file downloads.",
    )
    download_read_timeout: float = Field(
        default=120.0,
        description="HTTP read timeout in seconds for container file downloads. "
        "Applies per SDK attempt. The OpenAI SDK default of 600s is too generous "
        "for small generated files; a shorter timeout lets us retry sooner.",
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


@dataclass
class _FileState:
    phase: str = "pending"
    percent: int | None = None
    elapsed_seconds: float = 0.0
    retry_attempt: int = 0
    max_retries: int = 0


class _FileProgressTracker:
    """Concurrency-safe coordinator that publishes file download/upload progress
    to the user-visible assistant message in real time.

    Replaces sandbox links inline with progress text and appends a summary block.
    Throttles ``modify_assistant_message_async`` calls to avoid API spam.
    """

    def __init__(
        self,
        filenames: list[str],
        original_text: str,
        chat_service: ChatService,
        log: logging.LoggerAdapter[logging.Logger],
        min_publish_interval: float = 3.0,
    ) -> None:
        self._states: dict[str, _FileState] = {f: _FileState() for f in filenames}
        self._original_text = original_text
        self._chat_service = chat_service
        self._log = log
        self._lock = asyncio.Lock()
        self._last_publish_time = 0.0
        self._min_interval = min_publish_interval

    async def update(
        self,
        filename: str,
        phase: str,
        *,
        percent: int | None = None,
        elapsed_seconds: float = 0.0,
        retry_attempt: int = 0,
        max_retries: int = 0,
        force_publish: bool = False,
    ) -> None:
        lock_wait_t0 = time.monotonic()
        async with self._lock:
            lock_wait_ms = (time.monotonic() - lock_wait_t0) * 1000
            state = self._states.get(filename)
            if state is None:
                return
            state.phase = phase
            state.percent = percent
            state.elapsed_seconds = elapsed_seconds
            state.retry_attempt = retry_attempt
            state.max_retries = max_retries

            now = time.monotonic()
            should_publish = (
                force_publish
                or phase in ("done", "failed", "uploading")
                or now - self._last_publish_time >= self._min_interval
            )
            if should_publish:
                publish_t0 = time.monotonic()
                await self._publish()
                publish_ms = (time.monotonic() - publish_t0) * 1000
                self._last_publish_time = now
                if lock_wait_ms > 100 or publish_ms > 500:
                    lock_held_ms = (
                        time.monotonic() - lock_wait_t0
                    ) * 1000 - lock_wait_ms
                    self._log.warning(
                        "Tracker.update('%s', phase=%s): "
                        "lock_wait=%.0fms, publish=%.0fms, "
                        "lock_held=%.0fms",
                        filename,
                        phase,
                        lock_wait_ms,
                        publish_ms,
                        lock_held_ms,
                    )
            elif lock_wait_ms > 100:
                self._log.warning(
                    "Tracker.update('%s', phase=%s): lock_wait=%.0fms (no publish)",
                    filename,
                    phase,
                    lock_wait_ms,
                )

    async def tick_elapsed(self, filename: str, elapsed_seconds: float) -> None:
        """Publish an elapsed-time update without changing percent or retry state.

        Used by the background ticker to show time-based progress while the
        OpenAI API hasn't started returning bytes yet.
        """
        lock_wait_t0 = time.monotonic()
        async with self._lock:
            lock_wait_ms = (time.monotonic() - lock_wait_t0) * 1000
            state = self._states.get(filename)
            if state is None or state.phase != "downloading":
                return
            state.elapsed_seconds = elapsed_seconds
            now = time.monotonic()
            if now - self._last_publish_time >= self._min_interval:
                publish_t0 = time.monotonic()
                await self._publish()
                publish_ms = (time.monotonic() - publish_t0) * 1000
                self._last_publish_time = now
                if lock_wait_ms > 100 or publish_ms > 500:
                    lock_held_ms = (
                        time.monotonic() - lock_wait_t0
                    ) * 1000 - lock_wait_ms
                    self._log.warning(
                        "Tracker.tick_elapsed('%s'): "
                        "lock_wait=%.0fms, publish=%.0fms, "
                        "lock_held=%.0fms",
                        filename,
                        lock_wait_ms,
                        publish_ms,
                        lock_held_ms,
                    )
            elif lock_wait_ms > 100:
                self._log.warning(
                    "Tracker.tick_elapsed('%s'): lock_wait=%.0fms (no publish)",
                    filename,
                    lock_wait_ms,
                )

    async def publish_initial(self) -> None:
        """Send the first progress update (marks all files as pending)."""
        async with self._lock:
            for state in self._states.values():
                state.phase = "downloading"
            await self._publish()
            self._last_publish_time = time.monotonic()

    async def _publish(self) -> None:
        text = self._build_progress_text()
        try:
            t0 = time.monotonic()
            await self._chat_service.modify_assistant_message_async(content=text)
            publish_ms = (time.monotonic() - t0) * 1000
            if publish_ms > 500:
                self._log.warning(
                    "modify_assistant_message_async took %.0fms "
                    "(SDK singleton / backend contention suspected)",
                    publish_ms,
                )
        except Exception:
            self._log.debug("Failed to publish progress update", exc_info=True)

    def _build_progress_text(self) -> str:
        text = self._original_text

        for filename, state in self._states.items():
            if state.phase == "pending":
                continue
            progress = self._format_inline(filename, state)
            pattern = rf"!?\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"
            text = re.sub(pattern, progress, text)

        active = {
            f: s for f, s in self._states.items() if s.phase not in ("done", "pending")
        }
        if active:
            lines = ["---", "Preparing files:"]
            for filename, state in active.items():
                lines.append(f"- {filename} — {self._format_summary(state)}")
            text = text.rstrip() + "\n\n" + "\n".join(lines)

        return text

    @staticmethod
    def _format_inline(filename: str, state: _FileState) -> str:
        if state.phase == "downloading":
            base = f"Downloading {filename}..."
            if state.retry_attempt > 0:
                base += f" retry {state.retry_attempt}/{state.max_retries}"
            if state.percent is not None:
                return f"{base} {state.percent}%"
            if state.elapsed_seconds > 0:
                return f"{base} ({int(state.elapsed_seconds)}s)"
            return base
        if state.phase == "uploading":
            return f"Uploading {filename}..."
        if state.phase == "failed":
            return "File could not be generated. Please try again."
        return filename

    @staticmethod
    def _format_summary(state: _FileState) -> str:
        if state.phase == "downloading":
            base = "Downloading"
            if state.retry_attempt > 0:
                base += f" (retry {state.retry_attempt}/{state.max_retries})"
            if state.percent is not None:
                return f"{base} {state.percent}%"
            if state.elapsed_seconds > 0:
                return f"{base} ({int(state.elapsed_seconds)}s)"
            return f"{base}..."
        if state.phase == "uploading":
            return "Uploading..."
        if state.phase == "failed":
            return "Failed"
        return "Pending"


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

        self._log: logging.LoggerAdapter[logging.Logger] = _ChatLoggerAdapter(
            logger, {"chat_id": chat_id or "n/a"}
        )

        self._orphan_code_blocks: list[CodeInterpreterBlock] = []
        self._short_term_memory_manager = None
        if chat_id is not None and user_id is not None and company_id is not None:
            self._short_term_memory_manager = _init_short_term_memory_manager(
                company_id=company_id,
                user_id=user_id,
                chat_id=chat_id,
            )

    def _build_retry(self) -> AsyncRetrying:
        """Build a tenacity retry policy from the current config.

        Reused for both container-file downloads and knowledge-base uploads so
        that every I/O call gets the same exponential-backoff behaviour.
        """
        return AsyncRetrying(
            stop=stop_after_attempt(1 + self._config.max_download_retries),
            wait=wait_exponential(multiplier=self._config.download_retry_base_delay),
            before_sleep=before_sleep_log(self._log, logging.WARNING),  # type: ignore[arg-type]
            reraise=True,
        )

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        run_t0 = time.monotonic()
        self._log.info("run() started — fetching and uploading code interpreter files")

        container_files = loop_response.container_files
        self._log.info(
            "run() found %d container file annotation(s): %s",
            len(container_files),
            [cf.filename for cf in container_files],
        )

        phase_t0 = time.monotonic()
        try:
            self._content_map: dict[str, str | None] = await self._load_previous_files()  # type: ignore
            if self._content_map:
                self._log.info(
                    "run() loaded %d previous file(s) from short-term memory: %s",
                    len(self._content_map),
                    list(self._content_map.keys()),
                )
        except Exception:
            self._log.exception(
                "run() failed to load previous files from short-term memory; "
                "proceeding without previous file context."
            )
            self._content_map = {}
        load_ms = (time.monotonic() - phase_t0) * 1000

        tracker: _FileProgressTracker | None = None
        if container_files and self._chat_service is not None:
            tracker = _FileProgressTracker(
                filenames=[cf.filename for cf in container_files],
                original_text=loop_response.message.text or "",
                chat_service=self._chat_service,
                log=self._log,
                min_publish_interval=self._config.progress_update_interval,
            )
            await tracker.publish_initial()

        phase_t0 = time.monotonic()
        semaphore = asyncio.Semaphore(self._config.max_concurrent_file_downloads)
        tasks = [
            self._download_and_upload_container_files_to_knowledge_base(
                citation, semaphore, tracker
            )
            for citation in container_files
        ]
        results = await asyncio.gather(*tasks)
        download_upload_ms = (time.monotonic() - phase_t0) * 1000

        for citation, result in zip(container_files, results):
            self._content_map[citation.filename] = (
                result.content_id if result is not None else None
            )
            if result is None and tracker:
                await tracker.update(citation.filename, "failed", force_publish=True)

        succeeded = {f: cid for f, cid in self._content_map.items() if cid is not None}
        failed = [f for f, cid in self._content_map.items() if cid is None]
        self._log.info(
            "run() download/upload complete — %d succeeded, %d failed. "
            "succeeded=%s, failed=%s",
            len(succeeded),
            len(failed),
            list(succeeded.keys()),
            failed,
        )

        phase_t0 = time.monotonic()
        try:
            await self._save_generated_files(
                [
                    _ContentInfo(filename=filename, content_id=content_id)
                    for filename, content_id in self._content_map.items()
                    if content_id is not None
                ]
            )
        except Exception:
            self._log.exception(
                "run() failed to save generated files to short-term memory; "
                "file replacement will still proceed."
            )
        save_ms = (time.monotonic() - phase_t0) * 1000

        phase_t0 = time.monotonic()
        try:
            if feature_flags.enable_code_execution_fence_un_17972.is_enabled(
                self._company_id
            ):
                self._orphan_code_blocks = await self._upload_orphan_code_as_txt(
                    loop_response
                )
                if self._orphan_code_blocks:
                    self._log.info(
                        "run() produced %d orphan code block(s)",
                        len(self._orphan_code_blocks),
                    )
            else:
                self._orphan_code_blocks = []
        except Exception:
            self._log.exception(
                "run() failed to process orphan code blocks; "
                "file replacement will still proceed."
            )
            self._orphan_code_blocks = []
        orphan_ms = (time.monotonic() - phase_t0) * 1000

        total_ms = (time.monotonic() - run_t0) * 1000
        self._log.info(
            "run() finished — content_map has %d entries (%d ok, %d failed). "
            "Timing: total=%.0fms, load_stm=%.0fms, download_upload=%.0fms, "
            "save_stm=%.0fms, orphan=%.0fms",
            len(self._content_map),
            len(succeeded),
            len(failed),
            total_ms,
            load_ms,
            download_upload_ms,
            save_ms,
            orphan_ms,
        )

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        apply_t0 = time.monotonic()
        self._log.info(
            "apply_postprocessing started — %d file(s) in content_map, fence_ff=%s",
            len(self._content_map),
            feature_flags.enable_code_execution_fence_un_17972.is_enabled(
                self._company_id
            ),
        )

        if loop_response.message.references is None:
            loop_response.message.references = []
        if loop_response.message.text is None:
            loop_response.message.text = ""

        ref_number = _get_next_ref_number(loop_response.message.references)
        changed = False
        fence_ff_on = feature_flags.enable_code_execution_fence_un_17972.is_enabled(
            self._company_id
        )

        replaced_files: list[str] = []
        missed_files: list[str] = []
        error_files: list[str] = []

        for filename, content_id in self._content_map.items():
            if content_id is None:
                loop_response.message.text, replaced = _replace_container_file_error(
                    text=loop_response.message.text,
                    filename=filename,
                    error_message=self._config.file_download_failed_message,
                )
                changed |= replaced
                error_files.append(filename)
                continue

            mime = guess_type(filename)[0] or ""
            is_image = mime.startswith("image/")
            is_html = mime == "text/html"
            file_type = "image" if is_image else ("html" if is_html else "document")

            if is_image:
                loop_response.message.text, replaced = (
                    _replace_container_image_citation(
                        text=loop_response.message.text,
                        filename=filename,
                        content_id=content_id,
                    )
                )
                changed |= replaced

            elif is_html:
                loop_response.message.text, replaced = _replace_container_html_citation(
                    text=loop_response.message.text,
                    filename=filename,
                    content_id=content_id,
                )
                changed |= replaced

            else:
                loop_response.message.text, replaced = _replace_container_file_citation(
                    text=loop_response.message.text,
                    filename=filename,
                    content_id=content_id,
                    ref_number=ref_number,
                    use_content_link=fence_ff_on,
                )
                changed |= replaced

            if replaced:
                replaced_files.append(filename)
                self._log.info(
                    "Replaced sandbox link for '%s' (type=%s, content_id=%s)",
                    filename,
                    file_type,
                    content_id,
                )
            else:
                missed_files.append(filename)

            is_html_rendered = is_html
            has_superscript = f"<sup>{ref_number}</sup>" in loop_response.message.text
            if (
                replaced
                and has_superscript
                and not (is_image or is_html_rendered or fence_ff_on)
            ):
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

        self._log.info(
            "Stage-1 replacement summary — replaced=%s, missed=%s, error=%s",
            replaced_files,
            missed_files,
            error_files,
        )

        if fence_ff_on:
            code_blocks = _build_code_blocks(loop_response, self._content_map)
            self._log.info(
                "Fence injection — %d code block(s), files: %s",
                len(code_blocks),
                [f.filename for b in code_blocks for f in b.files],
            )
            unmatched_blocks = _warn_unmatched_code_blocks(
                self._content_map, code_blocks
            )
            if unmatched_blocks:
                self._log.info(
                    "Fence path: %d file(s) have no code-block match and will appear "
                    "as plain download links: %s",
                    len(unmatched_blocks),
                    list(unmatched_blocks),
                )
            text_before = loop_response.message.text
            loop_response.message.text = _inject_code_execution_fences(
                loop_response.message.text,
                code_blocks,
            )
            fences_changed = loop_response.message.text != text_before
            changed |= fences_changed
            if fences_changed:
                self._log.info("Fence injection modified the message text")

            if self._orphan_code_blocks:
                for block in self._orphan_code_blocks:
                    for file in block.files:
                        loop_response.message.references.append(
                            ContentReference(
                                sequence_number=ref_number,
                                source_id=file.content_id,
                                source="node-ingestion-chunks",
                                url=f"unique://content/{file.content_id}",
                                name=file.filename,
                            )
                        )
                        ref_number += 1
                changed = True
                self._log.info(
                    "Added %d orphan code block(s) to message references",
                    len(self._orphan_code_blocks),
                )

        _warn_missing_content_ids(loop_response.message.text, self._content_map)
        loop_response.message.text, dangling_replaced = _replace_dangling_sandbox_links(
            loop_response.message.text
        )
        changed |= dangling_replaced
        if dangling_replaced:
            self._log.warning(
                "apply_postprocessing found and replaced dangling sandbox links"
            )

        apply_ms = (time.monotonic() - apply_t0) * 1000
        self._log.info(
            "apply_postprocessing finished — changed=%s, replaced=%d, missed=%d, "
            "error=%d, dangling_cleaned=%s (%.0fms)",
            changed,
            len(replaced_files),
            len(missed_files),
            len(error_files),
            dangling_replaced,
            apply_ms,
        )

        return changed

    @override
    async def remove_from_text(self, text) -> str:
        return text

    @failsafe_async(failure_return_value=None, logger=logger)
    async def _download_and_upload_container_files_to_knowledge_base(
        self,
        container_file: AnnotationContainerFileCitation,
        semaphore: asyncio.Semaphore,
        tracker: _FileProgressTracker | None = None,
    ) -> _ContentInfo | None:
        async with semaphore:
            pipeline_t0 = time.monotonic()
            self._log.info(
                "Downloading container file '%s' (container=%s, file_id=%s)",
                container_file.filename,
                container_file.container_id,
                container_file.file_id,
            )

            download_t0 = time.monotonic()
            file_bytes = await self._download_file_bytes_with_progress(
                container_file, tracker
            )
            download_ms = (time.monotonic() - download_t0) * 1000

            self._log.info(
                "Downloaded container file '%s' (%d bytes, %.0fms)",
                container_file.filename,
                len(file_bytes),
                download_ms,
            )

            if tracker:
                await tracker.update(
                    container_file.filename, "uploading", force_publish=True
                )

            mime = guess_type(container_file.filename)[0] or "text/plain"
            self._log.info(
                "Uploading '%s' to knowledge base (mime=%s, %d bytes)",
                container_file.filename,
                mime,
                len(file_bytes),
            )

            assert self._chat_service is not None  # Checked in __init__
            upload_t0 = time.monotonic()
            content = await self._build_retry()(
                self._chat_service.upload_to_chat_from_bytes_async,
                content=file_bytes,
                content_name=container_file.filename,
                mime_type=mime,
                skip_ingestion=True,
                hide_in_chat=True,
            )
            upload_ms = (time.monotonic() - upload_t0) * 1000
            if upload_ms > 2000:
                self._log.warning(
                    "SDK upload for '%s' took %.0fms — "
                    "backend contention or slow blob storage suspected",
                    container_file.filename,
                    upload_ms,
                )

            if tracker:
                await tracker.update(
                    container_file.filename, "done", force_publish=True
                )

            pipeline_ms = (time.monotonic() - pipeline_t0) * 1000
            self._log.info(
                "Uploaded '%s' — content_id=%s. "
                "Timing: download=%.0fms, upload=%.0fms, pipeline=%.0fms",
                container_file.filename,
                content.id,
                download_ms,
                upload_ms,
                pipeline_ms,
            )
            return _ContentInfo(filename=container_file.filename, content_id=content.id)

    async def _download_file_bytes_with_progress(
        self,
        container_file: AnnotationContainerFileCitation,
        tracker: _FileProgressTracker | None,
    ) -> bytes:
        """Download container file with streaming progress and manual retry loop.

        Uses ``with_streaming_response`` so we can read ``content-length``
        and report download percentage.  Falls back to elapsed-time display
        when the header is absent.

        A background ticker task publishes elapsed-time updates at regular
        intervals even when the OpenAI API is slow to return the first byte.
        """
        max_attempts = 1 + self._config.max_download_retries
        download_start = time.monotonic()
        last_exception: Exception | None = None

        ticker_task: asyncio.Task[None] | None = None
        if tracker:

            async def _ticker() -> None:
                while True:
                    await asyncio.sleep(self._config.progress_update_interval)
                    elapsed = time.monotonic() - download_start
                    self._log.info(
                        "Still downloading '%s' (%.0fs elapsed)",
                        container_file.filename,
                        elapsed,
                    )
                    await tracker.tick_elapsed(container_file.filename, elapsed)

            ticker_task = asyncio.create_task(_ticker())

        try:
            for attempt_num in range(1, max_attempts + 1):
                retry_num = attempt_num - 1
                try:
                    if retry_num > 0:
                        delay = self._config.download_retry_base_delay * (
                            2 ** (retry_num - 1)
                        )
                        self._log.warning(
                            "Retrying download of '%s' (attempt %d/%d) after %.1fs",
                            container_file.filename,
                            attempt_num,
                            max_attempts,
                            delay,
                        )
                        if tracker:
                            await tracker.update(
                                container_file.filename,
                                "downloading",
                                elapsed_seconds=time.monotonic() - download_start,
                                retry_attempt=retry_num,
                                max_retries=self._config.max_download_retries,
                                force_publish=True,
                            )
                        await asyncio.sleep(delay)

                    return await self._stream_download_bytes(
                        container_file, tracker, retry_num, download_start
                    )
                except Exception as exc:
                    last_exception = exc
                    self._log.warning(
                        "Download attempt %d/%d failed for '%s': %s",
                        attempt_num,
                        max_attempts,
                        container_file.filename,
                        exc,
                    )

            assert last_exception is not None
            raise last_exception
        finally:
            if ticker_task is not None:
                ticker_task.cancel()
                try:
                    await ticker_task
                except BaseException:
                    pass

    async def _stream_download_bytes(
        self,
        container_file: AnnotationContainerFileCitation,
        tracker: _FileProgressTracker | None,
        retry_attempt: int,
        download_start: float,
    ) -> bytes:
        """Stream-download a single container file, reporting chunk-level progress.

        SDK-level retries are disabled (``max_retries=0``) so that only our
        manual retry loop retries, with full visibility in logs and progress
        tracker.  A shorter read timeout avoids waiting 10 minutes on a
        stalled connection.
        """
        t0 = time.monotonic()
        async with self._client.with_options(
            max_retries=0,
            timeout=httpx.Timeout(5.0, read=self._config.download_read_timeout),
        ).containers.files.content.with_streaming_response.retrieve(
            file_id=container_file.file_id,
            container_id=container_file.container_id,
        ) as response:
            first_byte_ms = (time.monotonic() - t0) * 1000
            self._log.info(
                "Stream opened for '%s' — first-byte latency=%.0fms, "
                "content-length=%s, status=%s",
                container_file.filename,
                first_byte_ms,
                response.headers.get("content-length", "unknown"),
                response.status_code,
            )
            content_length = response.headers.get("content-length")
            total = int(content_length) if content_length else None
            chunks: list[bytes] = []
            downloaded = 0
            last_chunk_time = time.monotonic()
            async for chunk in response.iter_bytes(
                chunk_size=self._config.download_chunk_size
            ):
                now = time.monotonic()
                chunk_gap_ms = (now - last_chunk_time) * 1000
                if chunk_gap_ms > 500:
                    self._log.warning(
                        "Download chunk gap for '%s': %.0fms "
                        "(downloaded=%d bytes so far)",
                        container_file.filename,
                        chunk_gap_ms,
                        downloaded,
                    )
                chunks.append(chunk)
                downloaded += len(chunk)
                if tracker:
                    pct = (downloaded * 100 // total) if total else None
                    elapsed = time.monotonic() - download_start
                    update_t0 = time.monotonic()
                    await tracker.update(
                        container_file.filename,
                        "downloading",
                        percent=pct,
                        elapsed_seconds=elapsed,
                        retry_attempt=retry_attempt,
                        max_retries=self._config.max_download_retries,
                    )
                    update_ms = (time.monotonic() - update_t0) * 1000
                    if update_ms > 200:
                        self._log.warning(
                            "tracker.update() blocked download stream for '%s' "
                            "for %.0fms (lock contention or slow modify_message)",
                            container_file.filename,
                            update_ms,
                        )
                last_chunk_time = time.monotonic()
            transfer_ms = (time.monotonic() - t0) * 1000 - first_byte_ms
            self._log.info(
                "Stream complete for '%s' — transfer=%.0fms, total=%d bytes",
                container_file.filename,
                transfer_ms,
                downloaded,
            )
            return b"".join(chunks)

    async def _load_previous_files(self) -> dict[str, str]:
        if self._short_term_memory_manager is None:
            return {}

        self._log.info(
            "Loading previously generated code interpreter files from short term memory"
        )
        t0 = time.monotonic()
        memory = await self._short_term_memory_manager.load_async()
        elapsed_ms = (time.monotonic() - t0) * 1000

        if memory is None:
            self._log.info(
                "No previously generated code interpreter files found "
                "in short term memory (%.0fms)",
                elapsed_ms,
            )
            return {}

        self._log.info(
            "Found %s previously generated code interpreter files (%.0fms)",
            len(memory.root),
            elapsed_ms,
        )

        return {content.filename: content.content_id for content in memory.root}

    async def _save_generated_files(self, content_infos: list[_ContentInfo]) -> None:
        if self._short_term_memory_manager is None or len(content_infos) == 0:
            return

        t0 = time.monotonic()
        await self._short_term_memory_manager.save_async(
            _DisplayedFilesShortTermMemorySchema(root=content_infos)
        )
        self._log.info(
            "Saved %d generated file(s) to short term memory (%.0fms)",
            len(content_infos),
            (time.monotonic() - t0) * 1000,
        )

    async def _upload_orphan_code_as_txt(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> list[CodeInterpreterBlock]:
        """Upload source **code** from calls that produced no container files as .txt artifacts.

        When code interpreter runs but generates no files or images, the response
        text has no sandbox links for fence injection to hook onto.  This method
        converts those "orphan" calls into downloadable .txt files (the executed
        code, not stdout) so the postprocessor can attach a reference for download.

        Called only when the fence feature flag is enabled.  Skipped entirely if
        any container files were produced (normal fencing handles those).
        """
        if loop_response.container_files:
            return []

        calls = loop_response.code_interpreter_calls
        if not calls:
            return []

        assert self._chat_service is not None  # Checked in __init__

        use_numeric_suffix = len(calls) > 1
        orphan_blocks: list[CodeInterpreterBlock] = []

        for i, call in enumerate(calls):
            if not call.code:
                continue

            # Always persist the executed source as the downloadable .txt (not stdout),
            # so the attachment matches what ran in the sandbox.
            txt_content = call.code
            filename = f"code_{i + 1}.txt" if use_numeric_suffix else "code.txt"

            try:
                content = await self._build_retry()(
                    self._chat_service.upload_to_chat_from_bytes_async,
                    content=txt_content.encode("utf-8"),
                    content_name=filename,
                    mime_type="text/plain",
                    skip_ingestion=True,
                    hide_in_chat=True,
                )
            except Exception:
                self._log.exception(
                    "Failed to upload orphan code block as txt for call %d ('%s'); "
                    "falling back to legacy code block display.",
                    i,
                    filename,
                )
                continue

            orphan_file = CodeInterpreterFile(
                filename=filename,
                content_id=content.id,
                type="document",
            )
            orphan_blocks.append(
                CodeInterpreterBlock(code=call.code, files=[orphan_file])
            )
            self._log.info(
                "Uploaded orphan code block as '%s' (content_id=%s)",
                filename,
                content.id,
            )

        return orphan_blocks


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
      excel       → .xlsx / .xls
      csv         → .csv
      word        → .docx / .doc
      powerpoint  → .pptx / .ppt
      pdf         → .pdf
      html        → .html / .htm
      image       → image/* MIME
      document    → fallback
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
        "pptx": "powerpoint",
        "ppt": "powerpoint",
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

    HTML is not emitted here in normal flow: it is rendered via ``HtmlRendering`` blocks
    in message text and excluded from fence injection. If ``type="html"`` is passed (e.g.
    orphan path), fall through to ``fileWithSource`` like other non-image artifacts.

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
      html     → [{filename}](unique://content/{content_id})
      document → [{filename}](unique://content/{content_id})
    """
    cid = re.escape(file.content_id)
    fname = re.escape(file.filename)
    if file.type == "image":
        return re.compile(rf"!\[image\]\(unique://content/{cid}\)")
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

    Three matching tiers are used in priority order:
      1. Primary: literal path ``/mnt/data/{filename}`` appears in the code.
      2. Secondary: the filename (with or without extension) appears as a quoted
         string literal — last-writer-wins among blocks (same as primary), but
         never overrides a primary match. Covers helper patterns such as:
           - stem only: ``save_fig(fig, "nvda_price_sma")``
           - full name: ``make_chart(kind, "random_line_chart.png", 42)``
      3. Last-resort: assign remaining unmatched files to the last code block —
         covers fully dynamic names built via f-strings or variable concatenation,
         e.g. ``f"/mnt/data/chart_{chart_type}_{i}.png"``, where no static token
         in the source matches the actual filename.
    Primary matches always take precedence over secondary ones; secondary always
    takes precedence over the last-resort fallback.
    """
    calls = loop_response.code_interpreter_calls

    # Step 1a: primary matching — full literal path /mnt/data/{filename} in code.
    # Last-writer-wins: later blocks overwrite earlier ones for the same file.
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

    # Snapshot primary matches only — secondary must not override these, but within
    # secondary we use last-writer-wins (later blocks overwrite earlier), same as 1a.
    primary_matched_filenames = set(file_to_block_idx.keys())

    # Step 1b: secondary matching for files not matched by primary.
    # Handles two common helper-function patterns where the full /mnt/data/ path
    # is never a literal string in the code:
    #
    #   Pattern A — stem only (no extension at the call site):
    #     save_fig(fig, "nvda_price_sma")  →  f"/mnt/data/{name}.png" at runtime
    #     → matches quoted stem "nvda_price_sma"
    #
    #   Pattern B — full filename at the call site:
    #     make_chart(kind, "random_line_chart.png", 42)
    #     fig.savefig(os.path.join(output_dir, filename), ...)
    #     → matches quoted full filename "random_line_chart.png"
    #
    # Last-writer-wins within secondary: do not skip when a prior block already matched
    # via secondary — only skip filenames that matched in Step 1a (primary).
    for idx, call in enumerate(calls):
        if not call.code:
            continue
        for annotation in loop_response.container_files:
            if annotation.filename in primary_matched_filenames:
                continue
            if content_map.get(annotation.filename) is None:
                continue
            fname = annotation.filename
            stem = fname.rsplit(".", 1)[0]
            quoted_fname = f'"{fname}"' in call.code or f"'{fname}'" in call.code
            quoted_stem = bool(stem) and (
                f'"{stem}"' in call.code or f"'{stem}'" in call.code
            )
            if quoted_fname or quoted_stem:
                file_to_block_idx[annotation.filename] = idx

    # Step 1c: last-resort fallback for files still unmatched after primary and secondary.
    # Covers Pattern C: filenames assembled entirely at runtime via f-strings or
    # variable concatenation, e.g. f"/mnt/data/chart_{chart_type}_{i}.png", where
    # no static string token in the code corresponds to the actual filename.
    # The last code block is used as the owner; when there is only one block this is
    # always correct. For multi-block responses it is a best-effort heuristic: the
    # worst outcome is the fence shows code from the wrong block, which is still
    # better than leaving the file as a bare inline image with no fence at all.
    last_block_idx: int | None = None
    for idx, call in enumerate(calls):
        if call.code:
            last_block_idx = idx
    if last_block_idx is not None:
        for annotation in loop_response.container_files:
            if annotation.filename in file_to_block_idx:
                continue
            if content_map.get(annotation.filename) is None:
                continue
            file_to_block_idx[annotation.filename] = last_block_idx

    # Step 2: group files by their owning block index, deduplicating by filename.
    # OpenAI may emit multiple annotations for the same filename when a file is
    # overwritten across executions. Using a dict keyed by filename ensures each
    # file appears exactly once per block (last annotation wins, consistent with
    # the last-writer-wins rule applied in step 1).
    # HTML files are excluded: they are always rendered via HtmlRendering blocks
    # and never participate in fence injection.
    block_file_map: dict[int, dict[str, CodeInterpreterFile]] = {}
    for annotation in loop_response.container_files:
        if _get_file_type(annotation.filename) == "html":
            continue
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
        if code is not None:
            result.append(
                CodeInterpreterBlock(code=code or "", files=list(files.values()))
            )
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

# Extracts the bare filename from a sandbox URL like `sandbox:/mnt/data/foo.csv`.
_SANDBOX_FILENAME_RE = re.compile(r"sandbox:/mnt/data/([^)\s]+)")


def _replace_dangling_sandbox_links(text: str) -> tuple[str, bool]:
    """Replace any remaining sandbox:/mnt/data/ markdown links with a per-file notice.

    A dangling link means either the LLM hallucinated a file reference (the sandbox
    link appears in the text but no matching container file annotation was emitted by
    OpenAI), or the link format did not match the expected regex in stage-1.  In both
    cases the user would see a broken link; this function replaces each such link with
    an actionable message that names the specific file, and logs a warning so the
    incident is visible in production logs.
    """
    if not _SANDBOX_MARKDOWN_LINK_RE.search(text):
        return text, False

    def _replacement(m: re.Match[str]) -> str:
        filename_match = _SANDBOX_FILENAME_RE.search(m.group())
        filename = filename_match.group(1) if filename_match else "the file"
        logger.warning(
            "Dangling sandbox link found in final text: '%s'. "
            "The file was either never uploaded or the link format did not match "
            "the expected pattern — replacing with per-file notice.",
            m.group(),
        )
        return f"⚠️ The file *{filename}* could not be retrieved. You can ask me to regenerate it."

    return _SANDBOX_MARKDOWN_LINK_RE.sub(_replacement, text), True


def _warn_unmatched_code_blocks(
    content_map: dict[str, str | None],
    code_blocks: list[CodeInterpreterBlock],
) -> dict[str, str]:
    """Warn for files that were uploaded but could not be matched to any code block.

    When the fence feature flag is on, every uploaded file should map to a code block
    via its /mnt/data/<filename> path so it can receive a fence.  If a file is not
    matched (e.g. the LLM used a variable for the output path rather than a literal
    string) it falls back to a plain unique://content/ link with no code context.
    The user can still download it, but the frontend artifact UI will not be shown.

    Returns:
        Mapping of filename → content_id for every file that could not be matched
        to a code block.  Callers may use this to inject additional fallback links.
    """
    fenced_filenames = {f.filename for block in code_blocks for f in block.files}
    unmatched: dict[str, str] = {}
    for filename, content_id in content_map.items():
        if content_id is None:
            continue
        if _get_file_type(filename) == "html":
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
            unmatched[filename] = content_id
    return unmatched


def _get_next_ref_number(references: list[ContentReference] | None) -> int:
    if not references:
        return 1
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
            "file was uploaded but the LLM did not reference it — appending fallback link.",
            filename,
            content_id,
        )
        fallback = f"\n\n📎 [{filename}](unique://content/{content_id})"
        return text + fallback, True

    logger.info("Inserting image citation for '%s'", filename)
    return re.sub(
        image_markdown,
        f"![image](unique://content/{content_id})",
        text,
    ), True


def _replace_container_html_citation(
    text: str, filename: str, content_id: str
) -> tuple[str, bool]:
    link_core = rf"!?\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"
    html_markdown = link_core

    if not re.search(html_markdown, text):
        logger.warning(
            "No sandbox link found for HTML file '%s' (content_id=%s); "
            "file was uploaded but the LLM did not reference it — appending fallback link.",
            filename,
            content_id,
        )
        fallback = f"\n\n📎 [{filename}](unique://content/{content_id})"
        return text + fallback, True

    logger.info("Inserting HTML rendering block for '%s'", filename)
    block = f"```HtmlRendering\n800px\n600px\n\nunique://content/{content_id}\n\n```"

    # Pattern 1 — link is the only non-whitespace content on its line (the common case
    # when the model writes the link as a list continuation on its own indented line).
    # Replace the FULL line (including leading whitespace) so the opening fence is
    # flush-left. Parsers require column-0 fences.
    # Also consume any whitespace-only lines immediately before the match so we don't
    # leave orphan indented blank lines above the block.
    line_only_link = re.compile(
        rf"(?m)^(?:[ \t]*\n)*[ \t]*{link_core}[ \t]*(?=\r?\n|$)"
    )
    if line_only_link.search(text):
        result = line_only_link.sub(block, text)
        return result, True

    # Pattern 2 — link shares a line with other content (e.g. "3. Dashboard: [link]").
    # Keep the label, then start the block on the next line.
    def _replace(m: re.Match[str]) -> str:
        start = m.start()
        line_start = text.rfind("\n", 0, start) + 1
        prefix_on_line = text[line_start:start].strip()
        leading = "\n" if prefix_on_line else ""
        # Ensure one blank line after the closing fence when followed by more text.
        end = m.end()
        trailing = "\n" if end < len(text) and not text[end:].startswith("\n") else ""
        return leading + block + trailing

    return re.sub(html_markdown, _replace, text), True


def _replace_container_file_citation(
    text: str,
    filename: str,
    content_id: str,
    ref_number: int,
    use_content_link: bool,
) -> tuple[str, bool]:
    """Replace a sandbox file link with either an inline content link or a superscript ref.

    When the fence feature flag is on (use_content_link=True), the sandbox link is
    replaced with [filename](unique://content/{id}) so the subsequent fence injection
    step can locate and wrap it. When the flag is off (use_content_link=False), the
    original pre-fence behaviour is restored: the link is replaced with <sup>N</sup>
    and the file remains accessible via the references panel.
    """
    file_markdown = rf"!?\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"

    if not re.search(file_markdown, text):
        logger.warning(
            "No sandbox link found for file '%s' (content_id=%s); "
            "file was uploaded but the LLM did not reference it — appending fallback link.",
            filename,
            content_id,
        )
        fallback = f"\n\n📎 [{filename}](unique://content/{content_id})"
        return text + fallback, True

    logger.info("Displaying file %s", filename)
    replacement = (
        f"[{filename}](unique://content/{content_id})"
        if use_content_link
        else f"<sup>{ref_number}</sup>"
    )
    return re.sub(file_markdown, replacement, text), True
