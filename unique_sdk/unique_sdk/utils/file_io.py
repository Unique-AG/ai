import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import requests

import unique_sdk
from unique_sdk.api_resources._content import Content


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


def _derive_preview_pdf_filename(displayed_filename: str) -> str:
    """Return ``<stem>_preview.pdf`` for *displayed_filename*.

    Keeps the preview blob filename predictable and collision-free with
    the original (which has the user-visible extension), while still
    making it obvious in storage which content the preview belongs to.
    """
    stem = displayed_filename.rsplit(".", 1)[0] or displayed_filename
    return f"{stem}_preview.pdf"


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
    preview_pdf_filename: str | None = None,
):
    """Upload *path_to_file* as a Unique :class:`Content`.

    When ``preview_pdf_path`` is provided, the caller gets a single-call
    Office → PDF preview flow: we attach a ``previewPdfFileName`` to the
    upserted content (so the platform mints a ``pdfPreviewWriteUrl``),
    PUT the original blob, then PUT the PDF preview blob. The chat side
    panel will pick the preview up automatically when rendering
    PowerPoint / Word / similar formats whose in-browser preview is
    unreliable.

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
            set, the upsert registers ``previewPdfFileName`` on the row
            and the PDF bytes are PUT to ``pdfPreviewWriteUrl`` after the
            original upload.
        preview_pdf_filename: Optional override for the blob filename
            stored against ``previewPdfFileName``. Defaults to
            ``<displayed_filename without extension>_preview.pdf`` so
            the preview blob is uniquely identifiable in storage.
    """
    # check that chatid or scope_or_unique_path is provided
    if not chat_id and not scope_or_unique_path:
        raise ValueError("chat_id or scope_or_unique_path must be provided")

    if preview_pdf_path is not None and not os.path.isfile(preview_pdf_path):
        raise ValueError(
            f"preview_pdf_path does not point to a readable file: {preview_pdf_path}"
        )

    size = os.path.getsize(path_to_file)
    resolved_preview_filename = preview_pdf_filename or (
        _derive_preview_pdf_filename(displayed_filename)
        if preview_pdf_path is not None
        else None
    )

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
        previewPdfFileName=resolved_preview_filename,
    )

    uploadUrl = createdContent.writeUrl

    # upload to azure blob storage SAS url uploadUrl the pdf file translatedFile make sure it is treated as a application/pdf
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

    # Attach the optional preview-PDF blob in the same call. We do this
    # *before* the second upsert so the byteSize patch and the preview
    # don't race; if the SAS URL is missing we surface a clear error
    # (the server only mints it when previewPdfFileName is set, so a
    # missing URL signals a server-side regression).
    if preview_pdf_path is not None:
        preview_write_url = createdContent.pdfPreviewWriteUrl
        if not preview_write_url:
            raise RuntimeError(
                "preview_pdf_path was provided but the upsert response carries "
                "no pdfPreviewWriteUrl — refusing to silently drop the preview. "
                "Verify the API gateway and node-ingestion expose "
                "previewPdfFileName on the upsert mutation."
            )
        _put_preview_pdf(preview_write_url, preview_pdf_path)

    if chat_id:
        unique_sdk.Content.upsert(
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
            previewPdfFileName=resolved_preview_filename,
        )
    else:
        unique_sdk.Content.upsert(
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
            previewPdfFileName=resolved_preview_filename,
        )

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
