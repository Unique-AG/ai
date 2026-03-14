"""
Unit tests for unique_toolkit.agentic.claude_agent.generated_files

Tests cover inject_file_references_into_text() — the main function that
resolves ./output/ path markers in Claude's response to platform content URLs.

Naming convention: test_<function>_<scenario>_<expected>
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.claude_agent.generated_files import (
    inject_file_references_into_text,
)
from unique_toolkit.agentic.claude_agent.workspace import (
    _upload_output_files,
)
from unique_toolkit.content.schemas import Content

CHAT_ID = "chat-test-abc"


# ─────────────────────────────────────────────────────────────────────────────
# inject_file_references_into_text — inline replacement
# ─────────────────────────────────────────────────────────────────────────────


class TestInjectFileReferencesIntoText:
    # ── No files ──────────────────────────────────────────────────────────────

    def test_empty_uploaded_files_returns_text_unchanged(self) -> None:
        """When no files were uploaded, text is returned verbatim."""
        original = "Here is your analysis."
        assert inject_file_references_into_text(original, {}) == original

    def test_empty_text_no_files_returns_empty(self) -> None:
        assert inject_file_references_into_text("", {}) == ""

    # ── Inline replacement — image ────────────────────────────────────────────

    def test_inline_image_reference_replaced_in_place(self) -> None:
        """./output/chart.png in markdown img syntax is replaced with platform URL."""
        text = "Here is the chart:\n\n![Sales over time](./output/chart.png)\n\nKey findings..."
        uploaded = {"chart.png": "cont_abc"}
        result = inject_file_references_into_text(text, uploaded)

        assert "unique://content/cont_abc" in result
        assert "./output/chart.png" not in result
        # Inline position: text before and after should still be present
        assert "Here is the chart:" in result
        assert "Key findings..." in result
        # No trailing separator since file was referenced inline
        assert "---" not in result

    def test_inline_image_markdown_syntax_preserved(self) -> None:
        """The ![alt](url) syntax is preserved, only the URL is replaced."""
        text = "![Revenue chart](./output/revenue.png)"
        uploaded = {"revenue.png": "cont_rev"}
        result = inject_file_references_into_text(text, uploaded)

        assert result == "![Revenue chart](unique://content/cont_rev)"

    def test_jpeg_inline_replaced(self) -> None:
        uploaded = {"photo.jpg": "cont_jpg"}
        text = "See photo: ![Photo](./output/photo.jpg)"
        result = inject_file_references_into_text(text, uploaded)
        assert "unique://content/cont_jpg" in result
        assert "./output/photo.jpg" not in result

    # ── Inline replacement — HTML ─────────────────────────────────────────────

    def test_inline_html_image_syntax_rewritten_to_html_rendering_block(self) -> None:
        """![title](./output/report.html) → HtmlRendering fenced block inline."""
        text = "Here is the dashboard:\n\n![Dashboard](./output/report.html)\n\nEOF"
        uploaded = {"report.html": "cont_html"}
        result = inject_file_references_into_text(text, uploaded)

        assert "```HtmlRendering" in result
        assert "unique://content/cont_html" in result
        assert "./output/report.html" not in result
        # Still inline — surrounding text preserved
        assert "Here is the dashboard:" in result
        assert "EOF" in result

    def test_inline_html_bare_path_replaced_with_url(self) -> None:
        """A bare ./output/file.html reference (no img syntax) is replaced too."""
        text = "View report at ./output/summary.html"
        uploaded = {"summary.html": "cont_s"}
        result = inject_file_references_into_text(text, uploaded)
        assert "unique://content/cont_s" in result
        assert "./output/summary.html" not in result

    # ── Inline replacement — non-image files ─────────────────────────────────

    def test_inline_csv_link_replaced_in_place(self) -> None:
        """[📎 data.csv](./output/data.csv) → [📎 data.csv](unique://content/{id})."""
        text = "Download the data: [📎 data.csv](./output/data.csv)\n\nNext section..."
        uploaded = {"data.csv": "cont_csv"}
        result = inject_file_references_into_text(text, uploaded)

        assert "unique://content/cont_csv" in result
        assert "./output/data.csv" not in result
        assert "Download the data:" in result
        assert "Next section..." in result
        assert "---" not in result

    # ── Fallback — unreferenced files appended at end ─────────────────────────

    def test_unreferenced_image_appended_at_end(self) -> None:
        """An uploaded image not mentioned in text is appended after a separator."""
        text = "Here is my analysis of the data."
        uploaded = {"chart.png": "cont_chart"}
        result = inject_file_references_into_text(text, uploaded)

        assert result.startswith(text)
        assert "\n\n---\n\n" in result
        assert "![chart.png](unique://content/cont_chart)" in result

    def test_unreferenced_html_appended_as_html_rendering_block(self) -> None:
        text = "Here is the summary."
        uploaded = {"report.html": "cont_r"}
        result = inject_file_references_into_text(text, uploaded)

        assert "```HtmlRendering" in result
        assert "unique://content/cont_r" in result

    def test_unreferenced_other_file_appended_as_download_link(self) -> None:
        text = "Analysis complete."
        uploaded = {"data.csv": "cont_d"}
        result = inject_file_references_into_text(text, uploaded)

        assert "[📎 data.csv](unique://content/cont_d)" in result

    # ── Mixed: some inline, some unreferenced ─────────────────────────────────

    def test_inline_file_not_duplicated_in_fallback(self) -> None:
        """A file referenced inline must NOT also appear in the fallback section."""
        text = "Chart: ![chart](./output/chart.png)\nExtra note."
        uploaded = {"chart.png": "cont_c"}
        result = inject_file_references_into_text(text, uploaded)

        # Appears exactly once (inline, not also in fallback)
        assert result.count("cont_c") == 1
        assert "---" not in result

    def test_mixed_inline_and_unreferenced(self) -> None:
        """Inline files are replaced in-place; unreferenced files appended."""
        text = "Chart: ![Sales](./output/chart.png)\nSee analysis above."
        uploaded = {"chart.png": "cont_c", "raw.csv": "cont_raw"}
        result = inject_file_references_into_text(text, uploaded)

        # chart replaced inline
        assert "unique://content/cont_c" in result
        assert "./output/chart.png" not in result
        # raw.csv appended at end
        assert "---" in result
        assert "[📎 raw.csv](unique://content/cont_raw)" in result

    def test_multiple_inline_files_all_replaced(self) -> None:
        """Multiple inline references in the same response are all replaced."""
        text = (
            "## Chart\n![Revenue](./output/rev.png)\n\n"
            "## Data\n[Download](./output/data.csv)\n"
        )
        uploaded = {"rev.png": "cont_r", "data.csv": "cont_d"}
        result = inject_file_references_into_text(text, uploaded)

        assert "unique://content/cont_r" in result
        assert "unique://content/cont_d" in result
        assert "./output/rev.png" not in result
        assert "./output/data.csv" not in result
        assert "---" not in result


# ─────────────────────────────────────────────────────────────────────────────
# _upload_output_files — return type tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_logger() -> MagicMock:
    return MagicMock()


class TestUploadOutputFilesReturnsContentIdMap:
    @pytest.mark.asyncio
    async def test_upload_returns_filename_to_content_id_map(
        self, tmp_path: Path
    ) -> None:
        """upload_output_files returns {filename: content_id} for uploaded files."""
        workspace_dir = tmp_path / "workspace"
        output_dir = workspace_dir / "output"
        output_dir.mkdir(parents=True)
        (output_dir / "chart.png").write_bytes(b"\x89PNG")

        mock_content = MagicMock(spec=Content)
        mock_content.id = "cont_returned_id"
        service = MagicMock()
        service.upload_content_from_bytes_async = AsyncMock(return_value=mock_content)

        result = await _upload_output_files(
            workspace_dir=workspace_dir,
            content_service=service,
            chat_id=CHAT_ID,
            logger=_make_logger(),
        )

        assert isinstance(result, dict)
        assert result == {"chart.png": "cont_returned_id"}

    @pytest.mark.asyncio
    async def test_empty_output_dir_returns_empty_dict(self, tmp_path: Path) -> None:
        workspace_dir = tmp_path / "workspace"
        (workspace_dir / "output").mkdir(parents=True)
        service = MagicMock()
        service.upload_content_from_bytes_async = AsyncMock(return_value=MagicMock())

        result = await _upload_output_files(
            workspace_dir=workspace_dir,
            content_service=service,
            chat_id=CHAT_ID,
            logger=_make_logger(),
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_upload_failure_omits_file_from_map(self, tmp_path: Path) -> None:
        """Files that fail to upload are omitted from the dict (no crash)."""
        workspace_dir = tmp_path / "workspace"
        output_dir = workspace_dir / "output"
        output_dir.mkdir(parents=True)
        (output_dir / "bad.csv").write_bytes(b"col1,col2")

        service = MagicMock()
        service.upload_content_from_bytes_async = AsyncMock(
            side_effect=RuntimeError("network error")
        )

        result = await _upload_output_files(
            workspace_dir=workspace_dir,
            content_service=service,
            chat_id=CHAT_ID,
            logger=_make_logger(),
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_multiple_files_all_in_map(self, tmp_path: Path) -> None:
        workspace_dir = tmp_path / "workspace"
        output_dir = workspace_dir / "output"
        output_dir.mkdir(parents=True)
        (output_dir / "a.txt").write_bytes(b"hello")
        (output_dir / "b.png").write_bytes(b"\x89PNG")

        call_count = 0

        async def _upload(**kwargs):  # type: ignore[return]
            nonlocal call_count
            call_count += 1
            content = MagicMock(spec=Content)
            content.id = f"cont_{kwargs['content_name']}"
            return content

        service = MagicMock()
        service.upload_content_from_bytes_async = AsyncMock(side_effect=_upload)

        result = await _upload_output_files(
            workspace_dir=workspace_dir,
            content_service=service,
            chat_id=CHAT_ID,
            logger=_make_logger(),
        )

        assert len(result) == 2
        assert result["a.txt"] == "cont_a.txt"
        assert result["b.png"] == "cont_b.png"
