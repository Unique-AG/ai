import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, TypedDict

import requests

import unique_sdk
from unique_sdk.api_resources._content import Content


class _PreviewKwargs(TypedDict, total=False):
    """Subset of ``Content.UpsertParams`` that we conditionally forward
    to ``upsert``. Typing it as a ``total=False`` TypedDict lets us
    expand ``**preview_kwargs`` without basedpyright assuming the dict
    could collide with non-string params like ``headers``."""

    previewPdfFileName: str


# download readUrl a random directory in /tmp
def download_file(url: str, filename: str):
    # Guard for callers without a type checker: fail fast with a clear error before reaching requests.
    if not isinstance(url, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise ValueError("URL must be a string.")  # pyright: ignore[reportUnreachable]
    # Create a random directory inside /tmp
    random_dir = tempfile.mkdtemp(dir="/tmp")

    # Create the full file path
    file_path = Path(random_dir) / filename

    # Download the file and save it to the random directory
    response = requests.get(url)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            file.write(response.content)
    else:
        raise Exception(f"Error downloading file: Status code {response.status_code}")

    return file_path


_PREVIEW_PDF_MIME_TYPE = "application/pdf"


def _put_preview_pdf(write_url: str, preview_pdf_path: str) -> None:
    """PUT *preview_pdf_path* bytes to the SAS URL returned by upsert."""
    with open(preview_pdf_path, "rb") as preview_file:
        response = requests.put(
            write_url,
            data=preview_file,
            headers={
                "X-Ms-Blob-Content-Type": _PREVIEW_PDF_MIME_TYPE,
                "X-Ms-Blob-Type": "BlockBlob",
            },
        )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Preview PDF upload failed with status {response.status_code}: "
            f"{response.text[:500]}"
        )


def upload_file(
    userId,
    companyId,
    path_to_file,
    displayed_filename,
    mime_type,
    description: str | None = None,
    scope_or_unique_path=None,
    chat_id=None,
    ingestion_config: Content.IngestionConfig | None = None,
    metadata: dict[str, Any] | None = None,
    preview_pdf_path: str | None = None,
):
    """Upload *path_to_file* as a Unique :class:`Content`.

    When ``preview_pdf_path`` is provided, the caller gets a single-call
    Office → PDF preview flow: the SDK does a two-upsert handshake — a
    first upsert to obtain the content id, then a finalize upsert that
    registers ``previewPdfFileName = f"{content.id}_pdfPreview"`` on
    the row and mints a ``pdfPreviewWriteUrl`` SAS URL the SDK PUTs the
    PDF bytes to.

    Naming the preview blob ``${content.id}_pdfPreview`` matches the
    convention used by the platform's ingestion worker
    (``next/services/node-ingestion-worker/src/pdf-preview-converter/pdf-preview-converter.service.ts``)
    and is collision-free across uploads sharing a ``displayed_filename``
    because content ids are globally unique. The platform stores the
    ``previewPdfFileName`` value verbatim — collision-free naming is a
    client contract, not a server invariant — so every client of
    node-ingestion (workers, SDKs, integrations) MUST follow this
    convention.

    Args:
        userId: Acting user id.
        companyId: Tenant id.
        path_to_file: Path to the original blob to upload.
        displayed_filename: Human-readable filename. Used as the content
            ``key`` and ``title``.
        mime_type: MIME type of the original blob.
        description: Optional description.
        scope_or_unique_path: Either a scope id, a folder path, or
            ``None`` (when uploading into a chat).
        chat_id: Chat id when uploading a chat attachment.
        ingestion_config: Ingestion options.
        metadata: Free-form metadata.
        preview_pdf_path: Optional path to a sibling PDF that should be
            rendered as the side-panel preview for this content. When
            set, the SDK derives the blob name from the upserted
            content id, registers it on the row via the finalize
            upsert, and PUTs the PDF bytes to the SAS URL the server
            returns in ``pdfPreviewWriteUrl``. Naming is the SDK's
            responsibility — there is no override kwarg, by design,
            so all callers land on the same ``${content.id}_pdfPreview``
            convention as the ingestion worker.
    """
    if not chat_id and not scope_or_unique_path:
        raise ValueError("chat_id or scope_or_unique_path must be provided")

    if preview_pdf_path is not None and not os.path.isfile(preview_pdf_path):
        raise ValueError(
            f"preview_pdf_path does not point to a readable file: {preview_pdf_path}"
        )

    size = os.path.getsize(path_to_file)

    # Step 1 — first upsert WITHOUT ``previewPdfFileName``. The id we
    # need to derive a collision-free preview blob name does not exist
    # yet; deriving from ``displayed_filename`` instead would race
    # across uploads sharing the same key (two ``report.pptx`` uploads
    # in the same company would overwrite each other's preview blob).
    createdContent = Content.upsert(
        user_id=userId,
        company_id=companyId,
        input={
            "key": displayed_filename,
            "title": displayed_filename,
            "mimeType": mime_type,
            "description": description,
            "ingestionConfig": ingestion_config,
            "metadata": metadata,
        },
        scopeId=scope_or_unique_path,
        chatId=chat_id,
    )

    # Step 2 — PUT the original bytes to the SAS URL minted by Step 1.
    uploadUrl = createdContent.writeUrl
    if uploadUrl is None:  # guard: writeUrl is Optional, basedpyright needs narrowing
        raise ValueError("createdContent.writeUrl is None")
    with open(path_to_file, "rb") as file:
        requests.put(
            uploadUrl,
            data=file,
            headers={
                "X-Ms-Blob-Content-Type": mime_type,
                "X-Ms-Blob-Type": "BlockBlob",
            },
        )

    # Step 3 — finalize upsert: ``byteSize`` + ``fileUrl`` flip the row
    # to bytes-on-blob, and (only when we have a preview to attach)
    # ``previewPdfFileName = f"{content.id}_pdfPreview"`` registers the
    # preview blob name on the row so the ``pdfPreviewWriteUrl`` field
    # resolver mints the SAS URL on this response.
    #
    # ``previewPdfFileName`` is forwarded as a conditional kwarg rather
    # than always-set-to-None; serializing ``"previewPdfFileName": null``
    # would tell the server to clear the field, which would silently
    # regress an existing-row re-upload that does not attach a preview.
    preview_kwargs: _PreviewKwargs = (
        {"previewPdfFileName": f"{createdContent.id}_pdfPreview"}
        if preview_pdf_path is not None
        else {}
    )

    if chat_id:
        finalizedContent = unique_sdk.Content.upsert(
            user_id=userId,
            company_id=companyId,
            input={
                "key": displayed_filename,
                "title": displayed_filename,
                "mimeType": mime_type,
                "description": description,
                "byteSize": size,
                "ingestionConfig": ingestion_config,
                "metadata": metadata,
            },
            fileUrl=createdContent.readUrl,
            chatId=chat_id,
            **preview_kwargs,
        )
    else:
        finalizedContent = unique_sdk.Content.upsert(
            user_id=userId,
            company_id=companyId,
            input={
                "key": displayed_filename,
                "title": displayed_filename,
                "mimeType": mime_type,
                "description": description,
                "byteSize": size,
                "ingestionConfig": ingestion_config,
                "metadata": metadata,
            },
            fileUrl=createdContent.readUrl,
            scopeId=scope_or_unique_path,
            **preview_kwargs,
        )

    # Step 4 — PUT the preview bytes (if requested). The SAS URL comes
    # from the FINALIZE response, not the first one, because the first
    # upsert did not carry ``previewPdfFileName`` and so could not have
    # minted ``pdfPreviewWriteUrl``.
    #
    # ``getattr`` so an older gateway that omits the field falls
    # through to the descriptive ``RuntimeError`` below instead of the
    # opaque ``AttributeError`` that ``UniqueObject.__getattr__`` would
    # otherwise raise on a missing key.
    if preview_pdf_path is not None:
        preview_write_url = getattr(finalizedContent, "pdfPreviewWriteUrl", None)
        if not preview_write_url:
            raise RuntimeError(
                "preview_pdf_path was provided but the finalize upsert "
                "response carries no pdfPreviewWriteUrl — refusing to "
                "silently drop the preview. Verify the API gateway and "
                "node-ingestion expose previewPdfFileName on the upsert "
                "mutation."
            )
        _put_preview_pdf(preview_write_url, preview_pdf_path)

    return createdContent


def download_content(
    companyId: str,
    userId: str,
    content_id: str,
    filename: str,
    chat_id: str | None = None,
):
    # Guard for callers without a type checker: f-string would silently coerce None to "None" otherwise.
    if not isinstance(content_id, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise ValueError("content_id must be a string.")  # pyright: ignore[reportUnreachable]
    url = f"{unique_sdk.api_base}/content/{content_id}/file"
    if chat_id:
        url = f"{url}?chatId={chat_id}"

    # Create a random directory inside /tmp
    random_dir = tempfile.mkdtemp(dir="/tmp")

    # Create the full file path
    file_path = Path(random_dir) / filename

    # Download the file and save it to the random directory
    headers = {
        "x-api-version": unique_sdk.api_version,
        "x-app-id": unique_sdk.app_id,
        "x-user-id": userId,
        "x-company-id": companyId,
        "Authorization": "Bearer %s" % (unique_sdk.api_key,),
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            file.write(response.content)
    else:
        raise Exception(f"Error downloading file: Status code {response.status_code}")

    return file_path


async def wait_for_ingestion_completion(
    user_id: str,
    company_id: str,
    content_id: str,
    chat_id: str | None = None,
    poll_interval: float = 1.0,
    max_wait: float = 60.0,
):
    """
    Polls until the content ingestion is finished or the maximum wait time is reached and throws in case ingestion fails. The function assumes that the content exists.
    """
    max_attempts = int(max_wait // poll_interval)
    for _ in range(max_attempts):
        searched_content = await Content.search_async(
            user_id=user_id,
            company_id=company_id,
            where={"id": {"equals": content_id}},
            chatId=chat_id,
            includeFailedContent=True,
        )
        if searched_content:
            ingestion_state = searched_content[0].get("ingestionState")
            if ingestion_state == "FINISHED":
                return ingestion_state
            if isinstance(ingestion_state, str) and ingestion_state.startswith(
                "FAILED"
            ):
                raise RuntimeError(f"Ingestion failed with state: {ingestion_state}")
        await asyncio.sleep(poll_interval)
    raise TimeoutError("Timed out waiting for file ingestion to finish.")
