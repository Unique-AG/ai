import logging
from mimetypes import guess_type

from openai.types.responses.response_output_text import AnnotationContainerFileCitation
from pydantic import BaseModel

from unique_toolkit import ChatService
from unique_toolkit._common.utils.files import FileMimeType, ImageMimeType
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


async def save_code_execution_artifact(
    chat_service: ChatService,
    file: AnnotationContainerFileCitation,
    file_bytes: bytes,
) -> Content:
    raw_mime = guess_type(file.filename)[0] or "text/plain"
    mime = _kb_safe_mime(raw_mime)

    if mime != raw_mime:
        _LOGGER.info(
            "MIME type '%s' is not supported by the Unique KB; "
            "uploading '%s' as 'text/plain' so the file can be stored and downloaded.",
            raw_mime,
            file.filename,
        )

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
        metadata={
            _CODE_EXECUTION_ARTIFACT_METADATA_KEY: CodeExecutionArtifactMetadata(
                container_id=file.container_id,
                file_id=file.file_id,
                filepath=f"/mnt/data/{file.filename}",
            ).model_dump()
        },
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
