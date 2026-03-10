"""
Unit tests for unique_toolkit.agentic.claude_agent.workspace

All ContentService calls are mocked — these tests are CI-safe and require
no real platform credentials. The workspace functions use stdlib only (zipfile,
shutil, pathlib, mimetypes) so no additional dependencies are needed.

Naming convention: test_<function>_<scenario>_<expected>
"""

from __future__ import annotations

import io
import zipfile
from logging import Logger
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.agentic.claude_agent.workspace import (
    CHECKPOINT_FILENAME,
    cleanup_workspace,
    persist_workspace,
    setup_workspace,
)
from unique_toolkit.content.schemas import Content

_WORKSPACE_PATCH = "unique_toolkit.agentic.claude_agent.workspace._TMP_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

CHAT_ID = "chat-test-123"


def _make_content(key: str, content_id: str = "cont_abc") -> Content:
    """Return a minimal Content object."""
    return Content(id=content_id, key=key)


def _make_zip(files: dict[str, bytes]) -> bytes:
    """Build an in-memory zip with the given {arcname: bytes} mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, data in files.items():
            zf.writestr(arcname, data)
    return buf.getvalue()


def _make_content_service(
    chat_contents: list[Content] | None = None,
    skill_contents: list[Content] | None = None,
    download_map: dict[str, bytes] | None = None,
) -> MagicMock:
    """Return a mocked ContentService with pre-configured async methods.

    Args:
        chat_contents: Files returned for ownerId searches.
        skill_contents: Files returned by list_contents_in_scope_async.
        download_map: Maps content_id → bytes for download calls.
    """
    service = MagicMock()
    download_map = download_map or {}

    async def _search(where: dict, chat_id: str = "") -> list[Content]:
        if "ownerId" in where:
            return chat_contents or []
        return []

    async def _list_scope(scope_id: str) -> list[Content]:
        return skill_contents or []

    async def _download(content_id: str, chat_id: str | None = None) -> bytes:
        return download_map.get(content_id, b"")

    async def _upload(**kwargs) -> Content:
        return MagicMock(spec=Content)

    service.search_contents_async = AsyncMock(side_effect=_search)
    service.list_contents_in_scope_async = AsyncMock(side_effect=_list_scope)
    service.download_content_to_bytes_async = AsyncMock(side_effect=_download)
    service.upload_content_from_bytes_async = AsyncMock(side_effect=_upload)
    return service


def _make_logger() -> MagicMock:
    return MagicMock(spec=Logger)


# ─────────────────────────────────────────────────────────────────────────────
# setup_workspace tests
# ─────────────────────────────────────────────────────────────────────────────


class TestSetupWorkspace:
    @pytest.mark.asyncio
    async def test_setup_workspace_creates_dir__when_no_chat_files(
        self, tmp_path: Path
    ) -> None:
        """Workspace directory is created even when there are no chat files."""
        service = _make_content_service(chat_contents=[])

        with patch(_WORKSPACE_PATCH, tmp_path):
            result = await setup_workspace(service, CHAT_ID, _make_logger())

        assert result.exists()
        assert result.is_dir()
        assert (result / "output").exists()

    @pytest.mark.asyncio
    async def test_setup_workspace_downloads_chat_files__when_files_exist(
        self, tmp_path: Path
    ) -> None:
        """Chat files are downloaded and written to the workspace root."""
        files = [
            _make_content("report.md", "cont_001"),
            _make_content("data.csv", "cont_002"),
        ]
        service = _make_content_service(
            chat_contents=files,
            download_map={
                "cont_001": b"# Report",
                "cont_002": b"col1,col2\n1,2",
            },
        )

        with patch(_WORKSPACE_PATCH, tmp_path):
            result = await setup_workspace(service, CHAT_ID, _make_logger())

        assert (result / "report.md").read_bytes() == b"# Report"
        assert (result / "data.csv").read_bytes() == b"col1,col2\n1,2"

    @pytest.mark.asyncio
    async def test_setup_workspace_restores_checkpoint__when_checkpoint_exists(
        self, tmp_path: Path
    ) -> None:
        """Checkpoint zip contents are extracted into the workspace."""
        zip_bytes = _make_zip({"notes.txt": b"prior turn notes"})
        checkpoint = _make_content(CHECKPOINT_FILENAME, "cont_ckpt")
        service = _make_content_service(
            chat_contents=[checkpoint],
            download_map={"cont_ckpt": zip_bytes},
        )

        with patch(_WORKSPACE_PATCH, tmp_path):
            result = await setup_workspace(service, CHAT_ID, _make_logger())

        assert (result / "notes.txt").read_bytes() == b"prior turn notes"

    @pytest.mark.asyncio
    async def test_setup_workspace_checkpoint_includes_claude_dir__when_zip_has_claude_dir(
        self, tmp_path: Path
    ) -> None:
        """~/.claude/ contents in the checkpoint are extracted correctly."""
        zip_bytes = _make_zip(
            {
                ".claude/session.json": b'{"session_id": "sess_abc"}',
                ".claude/skills/skill1.md": b"# Skill 1",
            }
        )
        checkpoint = _make_content(CHECKPOINT_FILENAME, "cont_ckpt")
        service = _make_content_service(
            chat_contents=[checkpoint],
            download_map={"cont_ckpt": zip_bytes},
        )

        with patch(_WORKSPACE_PATCH, tmp_path):
            result = await setup_workspace(service, CHAT_ID, _make_logger())

        assert (result / ".claude" / "session.json").exists()
        assert (result / ".claude" / "skills" / "skill1.md").exists()

    @pytest.mark.asyncio
    async def test_setup_workspace_first_turn_no_checkpoint__returns_empty_workspace(
        self, tmp_path: Path
    ) -> None:
        """When no checkpoint exists the workspace is fresh (first turn)."""
        service = _make_content_service(chat_contents=[])

        with patch(_WORKSPACE_PATCH, tmp_path):
            result = await setup_workspace(service, CHAT_ID, _make_logger())

        assert result.exists()
        # Only the output dir should be created — no other files.
        assert list(result.iterdir()) == [result / "output"]

    @pytest.mark.asyncio
    async def test_setup_workspace_corrupted_checkpoint__proceeds_gracefully(
        self, tmp_path: Path
    ) -> None:
        """A corrupted checkpoint zip is logged and ignored; workspace is still returned."""
        checkpoint = _make_content(CHECKPOINT_FILENAME, "cont_bad")
        service = _make_content_service(
            chat_contents=[checkpoint],
            download_map={"cont_bad": b"this is not a zip file"},
        )
        logger = _make_logger()

        with patch(_WORKSPACE_PATCH, tmp_path):
            result = await setup_workspace(service, CHAT_ID, logger)

        # Workspace still returned — not None.
        assert result.exists()
        # Warning was logged.
        logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_setup_workspace_downloads_skills__when_scope_id_configured(
        self, tmp_path: Path
    ) -> None:
        """Skill files are downloaded into .claude/skills/{skill-name}/SKILL.md."""
        # Content.key includes the skill subdirectory — e.g. "intro/SKILL.md"
        skill = _make_content("intro/SKILL.md", "cont_skill")
        service = _make_content_service(
            chat_contents=[],
            skill_contents=[skill],
            download_map={"cont_skill": b"---\nname: intro\n---\n# Intro skill"},
        )

        with patch(_WORKSPACE_PATCH, tmp_path):
            result = await setup_workspace(
                service, CHAT_ID, _make_logger(), skills_scope_id="scope-skills-1"
            )

        skill_file = result / ".claude" / "skills" / "intro" / "SKILL.md"
        assert skill_file.exists()
        assert b"# Intro skill" in skill_file.read_bytes()

    @pytest.mark.asyncio
    async def test_setup_workspace_no_skills__when_scope_id_is_none(
        self, tmp_path: Path
    ) -> None:
        """Skills are not downloaded when skills_scope_id is None."""
        service = _make_content_service(chat_contents=[])

        with patch(_WORKSPACE_PATCH, tmp_path):
            result = await setup_workspace(
                service, CHAT_ID, _make_logger(), skills_scope_id=None
            )

        # list_contents_in_scope_async must not have been called when scope_id is None.
        service.list_contents_in_scope_async.assert_not_called()
        # No skill subdirectories should have been created.
        assert not (result / ".claude" / "skills").exists()


# ─────────────────────────────────────────────────────────────────────────────
# persist_workspace tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPersistWorkspace:
    @pytest.mark.asyncio
    async def test_persist_workspace_uploads_output_files__when_output_dir_has_files(
        self, tmp_path: Path
    ) -> None:
        """Files in ./output/ are uploaded as chat attachments."""
        workspace_dir = tmp_path / CHAT_ID
        output_dir = workspace_dir / "output"
        output_dir.mkdir(parents=True)
        (output_dir / "result.txt").write_bytes(b"final answer")
        (output_dir / "chart.png").write_bytes(b"\x89PNG")

        service = _make_content_service()
        await persist_workspace(workspace_dir, service, CHAT_ID, _make_logger())

        # upload called at least for both output files + checkpoint
        upload_calls = service.upload_content_from_bytes_async.call_args_list
        uploaded_names = {c.kwargs["content_name"] for c in upload_calls}
        assert "result.txt" in uploaded_names
        assert "chart.png" in uploaded_names

    @pytest.mark.asyncio
    async def test_persist_workspace_saves_checkpoint_zip__always(
        self, tmp_path: Path
    ) -> None:
        """A checkpoint zip is always uploaded, even if output is empty."""
        workspace_dir = tmp_path / CHAT_ID
        (workspace_dir / "output").mkdir(parents=True)

        service = _make_content_service()
        await persist_workspace(workspace_dir, service, CHAT_ID, _make_logger())

        upload_calls = service.upload_content_from_bytes_async.call_args_list
        checkpoint_calls = [
            c for c in upload_calls if c.kwargs["content_name"] == CHECKPOINT_FILENAME
        ]
        assert len(checkpoint_calls) == 1
        # Verify it's a valid zip.
        zip_data = checkpoint_calls[0].kwargs["content"]
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            assert isinstance(zf.namelist(), list)

    @pytest.mark.asyncio
    async def test_persist_workspace_checkpoint_includes_claude_dir__when_present(
        self, tmp_path: Path
    ) -> None:
        """The .claude/ directory is included in the checkpoint zip."""
        workspace_dir = tmp_path / CHAT_ID
        (workspace_dir / "output").mkdir(parents=True)
        claude_dir = workspace_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "session.json").write_bytes(b'{"id": "sess_1"}')

        service = _make_content_service()
        await persist_workspace(workspace_dir, service, CHAT_ID, _make_logger())

        upload_calls = service.upload_content_from_bytes_async.call_args_list
        checkpoint_calls = [
            c for c in upload_calls if c.kwargs["content_name"] == CHECKPOINT_FILENAME
        ]
        zip_data = checkpoint_calls[0].kwargs["content"]
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            names = zf.namelist()
        assert ".claude/session.json" in names

    @pytest.mark.asyncio
    async def test_persist_workspace_no_output_dir__only_checkpoint_saved(
        self, tmp_path: Path
    ) -> None:
        """When ./output/ does not exist, only the checkpoint is uploaded."""
        workspace_dir = tmp_path / CHAT_ID
        workspace_dir.mkdir(parents=True)
        (workspace_dir / "scratch.py").write_bytes(b"x = 1")

        service = _make_content_service()
        await persist_workspace(workspace_dir, service, CHAT_ID, _make_logger())

        upload_calls = service.upload_content_from_bytes_async.call_args_list
        assert len(upload_calls) == 1
        assert upload_calls[0].kwargs["content_name"] == CHECKPOINT_FILENAME

    @pytest.mark.asyncio
    async def test_persist_workspace_upload_failure_does_not_raise__logs_warning(
        self, tmp_path: Path
    ) -> None:
        """An upload failure for an output file is logged but does not propagate."""
        workspace_dir = tmp_path / CHAT_ID
        (workspace_dir / "output").mkdir(parents=True)
        (workspace_dir / "output" / "report.md").write_bytes(b"# Hi")

        service = MagicMock()

        async def _flaky_upload(**kwargs):
            if kwargs.get("content_name") == "report.md":
                raise RuntimeError("network error")
            return MagicMock(spec=Content)

        service.upload_content_from_bytes_async = AsyncMock(side_effect=_flaky_upload)
        logger = _make_logger()

        # Should not raise.
        await persist_workspace(workspace_dir, service, CHAT_ID, logger)
        logger.warning.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# cleanup_workspace tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCleanupWorkspace:
    def test_cleanup_workspace_removes_dir__when_dir_exists(
        self, tmp_path: Path
    ) -> None:
        """cleanup_workspace removes the workspace directory."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "file.txt").write_bytes(b"data")

        cleanup_workspace(workspace_dir, _make_logger())

        assert not workspace_dir.exists()

    def test_cleanup_workspace_does_not_raise__when_dir_missing(self) -> None:
        """cleanup_workspace is idempotent — no error if dir already gone."""
        missing = Path("/tmp/claude-workspace/nonexistent-chat-xyz")
        cleanup_workspace(missing, _make_logger())  # must not raise
