"""
Workspace persistence for Claude Agent SDK (T1.1).

Lifecycle per turn:
  1. setup_workspace()   — create /tmp/claude-workspace/{chat_id}/, download chat
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

WORKSPACE_BASE = Path("/tmp/claude-workspace")
CHECKPOINT_FILENAME = "claude-workspace-checkpoint.zip"


async def setup_workspace(
    content_service: ContentService,
    chat_id: str,
    logger: Logger,
    skills_scope_id: str | None = None,
) -> Path:
    """Create workspace dir, download chat files, restore checkpoint, and load skills.

    Args:
        content_service: Platform content service for file operations.
        chat_id: Chat identifier — used as workspace subdirectory name.
        logger: Logger for diagnostics.
        skills_scope_id: KB scope containing skill files. If None, skill
            download is skipped.

    Returns:
        Path to the workspace directory (always created, even if setup fails).
    """
    workspace_dir = WORKSPACE_BASE / chat_id
    output_dir = workspace_dir / "output"

    workspace_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # List all files owned by this chat.
    chat_files: list[Content] = []
    try:
        chat_files = await content_service.search_contents_async(
            where={"ownerId": {"equals": chat_id}},
            chat_id=chat_id,
        )
    except Exception as e:
        logger.warning("workspace: failed to list chat files: %s", e)

    # Separate the checkpoint zip from regular chat files.
    checkpoint = None
    regular_files = []
    for content in chat_files:
        if content.key == CHECKPOINT_FILENAME:
            checkpoint = content
        else:
            regular_files.append(content)

    # Download regular chat files into workspace root.
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

    # Restore checkpoint zip (overwrites chat files if there is a conflict —
    # checkpoint is always the most recent state).
    if checkpoint is not None:
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
    else:
        logger.debug("workspace: no checkpoint found — fresh workspace for first turn")

    # Download skill files into .claude/skills/ so Claude can load them via
    # setting_sources=["project"].
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
        skill_files = await content_service.search_contents_async(
            where={"scopeId": {"equals": skills_scope_id}},
            chat_id=chat_id,
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
    """Upload each file in ./output/ as a chat attachment."""
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
