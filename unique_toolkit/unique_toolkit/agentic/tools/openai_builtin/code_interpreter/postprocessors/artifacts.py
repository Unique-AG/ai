import asyncio
import logging
import tempfile
from mimetypes import guess_type
from pathlib import Path
from typing import Any

import unique_sdk.utils.file_io as file_io
from pydantic import BaseModel

from unique_toolkit import ChatService
from unique_toolkit._common.utils.files import FileMimeType, ImageMimeType
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.office_preview import (
    OFFICE_PREVIEW_MIME_TYPES,
    convert_office_bytes_to_preview_pdf,
    office_extension,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.schemas import (
    CodeInterpreterContainerFile,
)
from unique_toolkit.content.schemas import Content

_CODE_EXECUTION_ARTIFACT_METADATA_KEY: str = "codeExecutionArtifactMetadata"

_LOGGER = logging.getLogger(__name__)


class CodeExecutionArtifactMetadata(BaseModel):
    container_id: str
    file_id: str
    filepath: str


def _kb_safe_mime(mime: str) -> str:
    """Return a MIME type the Unique KB will accept.

    Membership is defined by ``FileMimeType`` and ``ImageMimeType`` in
    ``unique_toolkit._common.utils.files`` (same catalog as path-based helpers
    like ``FileMimeType.is_valid_mime``, but here we already have a resolved
    MIME string from ``mimetypes.guess_type``, so we use StrEnum value lookup
    instead of re-parsing a path).

    The KB GraphQL API rejects many code-file MIME types (e.g. ``text/x-python``
    for ``.py`` files).  Anything not in those enums is coerced to
    ``text/plain`` so the file can be stored and downloaded without changing
    its bytes.

    Other ``image/*`` subtypes (e.g. ``image/jpg``) still pass through unchanged.
    """
    try:
        FileMimeType(mime)
        return mime
    except ValueError:
        pass
    try:
        ImageMimeType(mime)
        return mime
    except ValueError:
        pass
    if mime.startswith("image/"):
        return mime
    return "text/plain"


def _artifact_metadata(
    file: CodeInterpreterContainerFile,
) -> dict[str, Any]:
    return {
        _CODE_EXECUTION_ARTIFACT_METADATA_KEY: CodeExecutionArtifactMetadata(
            container_id=file.container_id,
            file_id=file.file_id,
            filepath=f"/mnt/data/{file.filename}",
        ).model_dump()
    }


async def _upload_artifact_bytes(
    chat_service: ChatService,
    file: CodeInterpreterContainerFile,
    file_bytes: bytes,
    mime: str,
) -> Content:
    _LOGGER.info(
        "Uploading '%s' to knowledge base (%d bytes, mime type %s)",
        file.filename,
        len(file_bytes),
        mime,
    )

    return await chat_service.upload_to_chat_from_bytes_async(
        content=file_bytes,
        content_name=file.filename,
        mime_type=mime,
        skip_ingestion=True,
        hide_in_chat=True,
        metadata=_artifact_metadata(file),
    )


async def _upload_office_artifact_with_preview(
    chat_service: ChatService,
    file: CodeInterpreterContainerFile,
    file_bytes: bytes,
    mime: str,
) -> Content | None:
    """Upload an Office artifact with a PDF preview, or ``None`` to fall back."""
    with tempfile.TemporaryDirectory(prefix="code-interpreter-preview-") as tmp:
        output_dir = Path(tmp)
        preview_path = await convert_office_bytes_to_preview_pdf(
            filename=file.filename,
            file_bytes=file_bytes,
            tmp_dir=output_dir,
            logger=_LOGGER,
        )
        if preview_path is None:
            _LOGGER.warning(
                "Code interpreter Office artifact '%s' could not be converted "
                "to PDF; uploading without preview.",
                file.filename,
            )
            return None

        source_path = output_dir / Path(file.filename).name
        _LOGGER.info(
            "Uploading code interpreter Office artifact '%s' with PDF preview '%s'",
            file.filename,
            preview_path.name,
        )

        uploaded = await asyncio.to_thread(
            file_io.upload_file,
            chat_service._user_id,
            chat_service._company_id,
            str(source_path),
            file.filename,
            mime,
            chat_id=chat_service._chat_id,
            ingestion_config={
                "uniqueIngestionMode": "SKIP_INGESTION",
                "hideInChat": True,
            },
            metadata=_artifact_metadata(file),
            preview_pdf_path=str(preview_path),
        )

    return Content.model_validate(uploaded, by_alias=True, by_name=True)


async def save_code_execution_artifact(
    chat_service: ChatService,
    file: CodeInterpreterContainerFile,
    file_bytes: bytes,
    *,
    attach_office_preview: bool = False,
) -> Content:
    """Upload a code-interpreter artifact to the chat knowledge base.

    ``attach_office_preview`` is opt-in (default ``False``) so existing
    Unique AI callers keep the historical bytes-only upload. When ``True``,
    Word / PowerPoint / Excel files are converted to a sibling PDF and
    uploaded with ``preview_pdf_path``. Conversion is best-effort: if
    LibreOffice is missing or conversion fails, the original bytes are
    uploaded instead. Upload failures are not retried via the bytes path,
    because ``file_io.upload_file`` may already have created a content row.
    """
    if attach_office_preview:
        extension = office_extension(file.filename)
        if extension is not None:
            mime = _kb_safe_mime(OFFICE_PREVIEW_MIME_TYPES[extension])
            content = await _upload_office_artifact_with_preview(
                chat_service=chat_service,
                file=file,
                file_bytes=file_bytes,
                mime=mime,
            )
            if content is not None:
                return content
            return await _upload_artifact_bytes(
                chat_service=chat_service,
                file=file,
                file_bytes=file_bytes,
                mime=mime,
            )

    raw_mime = guess_type(file.filename)[0] or "text/plain"
    mime = _kb_safe_mime(raw_mime)

    if mime != raw_mime:
        _LOGGER.info(
            "MIME type '%s' is not supported by the Unique KB; "
            "uploading '%s' as 'text/plain' so the file can be stored and downloaded.",
            raw_mime,
            file.filename,
        )

    return await _upload_artifact_bytes(
        chat_service=chat_service,
        file=file,
        file_bytes=file_bytes,
        mime=mime,
    )


def load_code_execution_metadata(
    content: Content,
) -> CodeExecutionArtifactMetadata | None:
    if (
        content.metadata is None
        or _CODE_EXECUTION_ARTIFACT_METADATA_KEY not in content.metadata
    ):
        return None

    return CodeExecutionArtifactMetadata.model_validate(
        content.metadata[_CODE_EXECUTION_ARTIFACT_METADATA_KEY]
    )
