"""LibreOffice PDF previews for code-interpreter Office artifacts.

When the OpenAI code interpreter emits a Word, PowerPoint, or Excel file,
the chat UI can render a sibling PDF in the side panel far more reliably
than the Office binary. Conversion is best-effort: if ``soffice`` is
missing, times out, or rejects the file, callers upload the original
without a preview.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

_SOFFICE_TIMEOUT_SECONDS = 180

# Canonical MIME types so slim containers without ``/etc/mime.types`` still
# upload Office files with a KB-accepted type instead of falling back to
# ``text/plain`` via ``mimetypes.guess_type``.
OFFICE_PREVIEW_MIME_TYPES: dict[str, str] = {
    ".doc": "application/msword",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ),
    ".xls": "application/vnd.ms-excel",
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}


def office_extension(filename: str) -> str | None:
    """Return the lowercased Office suffix, or ``None`` if not previewable."""
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in OFFICE_PREVIEW_MIME_TYPES else None


def _resolve_soffice_binary() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def _run_soffice(
    soffice: str,
    source: Path,
    output_dir: Path,
    logger: logging.Logger,
) -> None:
    """Invoke headless ``soffice`` to convert *source* into *output_dir*.

    Uses an isolated ``UserInstallation`` profile so concurrent LibreOffice
    invocations do not collide on ``$HOME/.config/libreoffice``.
    """
    with tempfile.TemporaryDirectory(
        prefix=".libreoffice-profile-",
        dir=output_dir,
    ) as profile_dir:
        proc = subprocess.run(
            [
                soffice,
                f"-env:UserInstallation={Path(profile_dir).resolve().as_uri()}",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=_SOFFICE_TIMEOUT_SECONDS,
        )
    if proc.returncode != 0:
        logger.warning(
            "office_preview: soffice exited %d for '%s' "
            "(stdout=%d bytes, stderr=%d bytes)",
            proc.returncode,
            source.name,
            len((proc.stdout or "").strip()),
            len((proc.stderr or "").strip()),
        )
        raise subprocess.CalledProcessError(
            proc.returncode, proc.args, proc.stdout, proc.stderr
        )


async def convert_office_bytes_to_preview_pdf(
    filename: str,
    file_bytes: bytes,
    tmp_dir: Path,
    logger: logging.Logger,
) -> Path | None:
    """Write *file_bytes* into *tmp_dir* and convert to a sibling preview PDF.

    The original file is written as ``tmp_dir / Path(filename).name`` so the
    caller can pass that path to the SDK uploader. The preview is rendered
    into ``tmp_dir / .previews / <stem>.pdf`` so it cannot collide with a
    same-named PDF the interpreter also produced.

    Returns the preview path, or ``None`` when conversion is unavailable or
    fails. Never raises for expected conversion problems.
    """
    safe_filename = Path(filename).name
    source_path = tmp_dir / safe_filename
    source_path.write_bytes(file_bytes)

    soffice = _resolve_soffice_binary()
    if soffice is None:
        logger.warning(
            "office_preview: soffice/libreoffice not found on PATH — "
            "uploading '%s' without a PDF preview.",
            safe_filename,
        )
        return None

    previews_dir = tmp_dir / ".previews"
    previews_dir.mkdir(exist_ok=True)
    target = previews_dir / f"{source_path.stem}.pdf"

    try:
        await asyncio.to_thread(
            _run_soffice, soffice, source_path, previews_dir, logger
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "office_preview: soffice timed out after %ds for '%s' — "
            "uploading original only",
            _SOFFICE_TIMEOUT_SECONDS,
            safe_filename,
        )
        return None
    except subprocess.CalledProcessError:
        return None
    except Exception:
        logger.exception(
            "office_preview: unexpected error for '%s' — uploading original only",
            safe_filename,
        )
        return None

    if target.is_file():
        return target

    logger.warning(
        "office_preview: soffice returned 0 but '%s' is missing for '%s'",
        target.name,
        safe_filename,
    )
    return None
