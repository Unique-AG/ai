"""
Workspace persistence for Claude Agent SDK (T1.1).

Lifecycle per turn:
  1. setup_workspace()   — create /tmp/{chat_id}-claude-workspace/, download chat
                          files, restore checkpoint zip (incl. ~/.claude/ session
                          state), download skills into .claude/skills/.
  2. Claude runs with cwd=workspace_dir.
  3. persist_workspace() — upload files from ./output/ to chat, zip the full
                          workspace (incl. .claude/) and save as the checkpoint.
  4. cleanup_workspace() — shutil.rmtree() the local dir.

Error contract:
  All public functions catch and log errors rather than re-raising. A failed
  workspace setup must not prevent the Claude loop from running; teardown
  failures must not surface to the user.
"""

from __future__ import annotations

import io
import mimetypes
import shutil
import zipfile
from logging import Logger
from pathlib import Path

from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService

# Parent directory for all chat workspaces. Private — tests patch this to tmp_path.
_TMP_DIR = Path("/tmp")
CHECKPOINT_FILENAME = "claude-workspace-checkpoint.zip"


def _get_workspace_dir(chat_id: str) -> Path:
    """Return the workspace directory path for a given chat ID.

    Format: /tmp/{chat_id}-claude-workspace — chat_id as prefix makes workspaces
    easy to identify, isolate, and clean up per chat.
    """
    return _TMP_DIR / f"{chat_id}-claude-workspace"


def _create_workspace_dirs(workspace_dir: Path) -> None:
    """Create workspace root and output/ subdirectory."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "output").mkdir(parents=True, exist_ok=True)


async def _download_chat_files(
    content_service: ContentService,
    chat_id: str,
    workspace_dir: Path,
    logger: Logger,
) -> tuple[Content | None, list[Content]]:
    """List all chat files, download regular files to workspace, separate checkpoint.

    unique_sdk.utils.file_io exists but is synchronous and lacks skip_ingestion
    support. ContentService is used here for async compatibility and
    skip_ingestion=True on checkpoints.

    Returns (checkpoint_content_or_None, regular_files_list).
    """
    chat_files: list[Content] = []
    try:
        chat_files = await content_service.search_contents_async(
            where={"ownerId": {"equals": chat_id}},
            chat_id=chat_id,
        )
    except Exception as e:
        logger.warning("workspace: failed to list chat files: %s", e)

    checkpoint = None
    regular_files = []
    for content in chat_files:
        if content.key == CHECKPOINT_FILENAME:
            checkpoint = content
        else:
            regular_files.append(content)

    for content in regular_files:
        try:
            file_bytes = await content_service.download_content_to_bytes_async(
                content_id=content.id,
                chat_id=chat_id,
            )
            dest = workspace_dir / content.key
            dest.parent.mkdir(parents=True, exist_ok=True)
            _ = dest.write_bytes(file_bytes)
            logger.debug("workspace: downloaded chat file %s", content.key)
        except Exception as e:
            logger.warning(
                "workspace: failed to download chat file %s: %s", content.key, e
            )

    return checkpoint, regular_files


async def _restore_checkpoint(
    content_service: ContentService,
    chat_id: str,
    workspace_dir: Path,
    checkpoint: Content,
    logger: Logger,
) -> None:
    """Download and extract the checkpoint zip into workspace_dir.

    unique_sdk.utils.file_io exists but is synchronous and lacks skip_ingestion
    support. ContentService is used here for async compatibility and
    skip_ingestion=True on checkpoints.
    """
    try:
        zip_bytes = await content_service.download_content_to_bytes_async(
            content_id=checkpoint.id,
            chat_id=chat_id,
        )
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(workspace_dir)
        logger.debug("workspace: checkpoint restored from %s", CHECKPOINT_FILENAME)
    except zipfile.BadZipFile as e:
        logger.warning(
            "workspace: checkpoint zip is corrupted — starting with fresh workspace: %s",
            e,
        )
    except Exception as e:
        logger.warning("workspace: failed to restore checkpoint: %s", e)


async def setup_workspace(
    content_service: ContentService,
    chat_id: str,
    logger: Logger,
    skills_scope_id: str | None = None,
) -> Path:
    """Create workspace dir, download chat files, restore checkpoint, and load skills.

    Args:
        content_service: Platform content service for file operations.
        chat_id: Chat identifier — used as workspace directory name prefix.
        logger: Logger for diagnostics.
        skills_scope_id: KB scope containing skill files. If None, skill
            download is skipped.

    Returns:
        Path to the workspace directory (always created, even if setup fails).
    """
    workspace_dir = _get_workspace_dir(chat_id)
    _create_workspace_dirs(workspace_dir)

    checkpoint, _ = await _download_chat_files(
        content_service=content_service,
        chat_id=chat_id,
        workspace_dir=workspace_dir,
        logger=logger,
    )

    if checkpoint is not None:
        await _restore_checkpoint(
            content_service=content_service,
            chat_id=chat_id,
            workspace_dir=workspace_dir,
            checkpoint=checkpoint,
            logger=logger,
        )
    else:
        logger.debug("workspace: no checkpoint found — fresh workspace for first turn")

    if skills_scope_id is not None:
        await _download_skills(
            content_service=content_service,
            workspace_dir=workspace_dir,
            chat_id=chat_id,
            skills_scope_id=skills_scope_id,
            logger=logger,
        )

    return workspace_dir


async def _download_skills(
    content_service: ContentService,
    workspace_dir: Path,
    chat_id: str,
    skills_scope_id: str,
    logger: Logger,
) -> None:
    """Download skill files from KB into {workspace}/.claude/skills/."""
    skills_dir = workspace_dir / ".claude" / "skills"
    try:
        skill_files = await content_service.list_contents_in_scope_async(
            skills_scope_id
        )
    except Exception as e:
        logger.warning(
            "workspace: failed to list skills from scope %s: %s", skills_scope_id, e
        )
        return

    if not skill_files:
        logger.debug("workspace: no skills found in scope %s", skills_scope_id)
        return

    skills_dir.mkdir(parents=True, exist_ok=True)
    for skill in skill_files:
        try:
            skill_bytes = await content_service.download_content_to_bytes_async(
                content_id=skill.id,
                chat_id=chat_id,
            )
            dest = skills_dir / skill.key
            dest.parent.mkdir(parents=True, exist_ok=True)
            _ = dest.write_bytes(skill_bytes)
            logger.debug("workspace: downloaded skill %s", skill.key)
        except Exception as e:
            logger.warning("workspace: failed to download skill %s: %s", skill.key, e)


async def persist_workspace(
    workspace_dir: Path,
    content_service: ContentService,
    chat_id: str,
    logger: Logger,
) -> None:
    """Upload output files and save the full workspace as a checkpoint zip.

    Output files (in ./output/) are uploaded as chat attachments visible to the
    user. The checkpoint zip is internal-only (skip_ingestion=True) and contains
    the full workspace including .claude/ session state.

    Args:
        workspace_dir: Local workspace directory path.
        content_service: Platform content service for file operations.
        chat_id: Chat identifier — used as the file owner.
        logger: Logger for diagnostics.
    """
    await _upload_output_files(
        workspace_dir=workspace_dir,
        content_service=content_service,
        chat_id=chat_id,
        logger=logger,
    )
    await _save_checkpoint(
        workspace_dir=workspace_dir,
        content_service=content_service,
        chat_id=chat_id,
        logger=logger,
    )


async def _upload_output_files(
    workspace_dir: Path,
    content_service: ContentService,
    chat_id: str,
    logger: Logger,
) -> None:
    """Upload each file in ./output/ as a chat attachment.

    unique_sdk.utils.file_io exists but is synchronous and lacks skip_ingestion
    support. ContentService is used here for async compatibility and
    skip_ingestion=True on checkpoints.
    """
    output_dir = workspace_dir / "output"
    if not output_dir.exists():
        logger.debug("workspace: no output dir — skipping output upload")
        return

    output_files = [f for f in output_dir.iterdir() if f.is_file()]
    if not output_files:
        logger.debug("workspace: output dir is empty — skipping output upload")
        return

    for output_file in output_files:
        try:
            file_bytes = output_file.read_bytes()
            mime_type, _ = mimetypes.guess_type(output_file.name)
            mime_type = mime_type or "application/octet-stream"
            _ = await content_service.upload_content_from_bytes_async(
                content=file_bytes,
                content_name=output_file.name,
                mime_type=mime_type,
                chat_id=chat_id,
                skip_ingestion=True,
            )
            logger.debug("workspace: uploaded output file %s", output_file.name)
        except Exception as e:
            logger.warning(
                "workspace: failed to upload output file %s: %s", output_file.name, e
            )


async def _save_checkpoint(
    workspace_dir: Path,
    content_service: ContentService,
    chat_id: str,
    logger: Logger,
) -> None:
    """Zip the full workspace (including .claude/) and upload as checkpoint."""
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(
            zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            for file_path in workspace_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(workspace_dir)
                    zf.write(file_path, arcname)

        zip_bytes = zip_buffer.getvalue()
        _ = await content_service.upload_content_from_bytes_async(
            content=zip_bytes,
            content_name=CHECKPOINT_FILENAME,
            mime_type="application/zip",
            chat_id=chat_id,
            skip_ingestion=True,
        )
        logger.debug("workspace: checkpoint saved (%d bytes)", len(zip_bytes))
    except Exception as e:
        logger.error("workspace: failed to save checkpoint: %s", e, exc_info=True)


def cleanup_workspace(workspace_dir: Path, logger: Logger) -> None:
    """Remove the local workspace directory after persist completes.

    Uses ignore_errors=True so a partial cleanup never raises.
    """
    shutil.rmtree(workspace_dir, ignore_errors=True)
    logger.debug("workspace: cleaned up %s", workspace_dir)
