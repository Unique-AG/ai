"""Tests for log redaction helpers."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from unique_toolkit.log_redaction import (
    CID_SAFE_MARKER,
    get_cid_safe_logger,
    redact_args,
    redact_body_preview,
    redact_filename,
    redact_filenames,
    redact_path,
    redact_text,
    redact_uploaded_files,
)


class TestRedactFilename:
    def test_simple_extension_kept(self) -> None:
        assert redact_filename("Q3 2025 earnings call.docx") == "<redacted>.docx"

    def test_compound_extension_kept(self) -> None:
        assert redact_filename("notes.tar.gz") == "<redacted>.tar.gz"

    def test_no_extension(self) -> None:
        assert redact_filename("README") == "<redacted>"

    def test_none_returns_redacted(self) -> None:
        assert redact_filename(None) == "<redacted>"

    def test_empty_returns_redacted(self) -> None:
        assert redact_filename("") == "<redacted>"

    def test_pathlike_input(self) -> None:
        assert (
            redact_filename(Path("/tmp/abc-workspace/output/chart.png"))
            == "<redacted>.png"
        )

    def test_content_id_appended(self) -> None:
        assert (
            redact_filename("Top Secret Q3.pdf", content_id="cnt_123")
            == "<redacted>.pdf (id=cnt_123)"
        )

    def test_content_id_with_no_extension(self) -> None:
        assert (
            redact_filename("Customer List", content_id="cnt_xyz")
            == "<redacted> (id=cnt_xyz)"
        )

    def test_extension_sanitised(self) -> None:
        result = redact_filename("evil.docx; rm -rf /")
        assert result.startswith("<redacted>")
        assert ";" not in result
        assert " " not in result
        assert "evil" not in result


class TestRedactPath:
    def test_keeps_parent(self) -> None:
        assert (
            redact_path("/tmp/chat-id-workspace/output/secret.docx")
            == "/tmp/chat-id-workspace/output/<redacted>.docx"
        )

    def test_relative_no_parent(self) -> None:
        assert redact_path("secret.docx") == "<redacted>.docx"

    def test_none(self) -> None:
        assert redact_path(None) == "<redacted>"

    def test_empty(self) -> None:
        assert redact_path("") == "<redacted>"


class TestRedactFilenames:
    def test_list_redaction(self) -> None:
        assert redact_filenames(["a.txt", "Customer List.pdf", "RUN.LOG"]) == [
            "<redacted>.txt",
            "<redacted>.pdf",
            "<redacted>.LOG",
        ]

    def test_none(self) -> None:
        assert redact_filenames(None) == []


class TestRedactUploadedFiles:
    def test_uploads(self) -> None:
        rendered = redact_uploaded_files(
            {
                "Confidential Q3 2025.pdf": "cnt_1",
                "chart.png": "cnt_2",
            }
        )
        assert rendered == [
            "<redacted>.pdf (id=cnt_1)",
            "<redacted>.png (id=cnt_2)",
        ]

    def test_empty(self) -> None:
        assert redact_uploaded_files({}) == []
        assert redact_uploaded_files(None) == []


class TestRedactText:
    def test_preserves_length(self) -> None:
        assert redact_text("hello world") == "<redacted text 11 chars>"

    def test_custom_label(self) -> None:
        assert redact_text("hi", label="prompt") == "<redacted prompt 2 chars>"

    def test_none(self) -> None:
        assert redact_text(None) == "<redacted text none>"

    def test_empty(self) -> None:
        assert redact_text("") == "<redacted text empty>"

    def test_does_not_include_content(self) -> None:
        sensitive = "API_KEY=sk-abc123 user said hi"
        result = redact_text(sensitive, label="prompt")
        assert "sk-abc123" not in result
        assert "user said hi" not in result


class TestRedactArgs:
    def test_dict_keys_only(self) -> None:
        out = redact_args({"command": "ls -la /etc/passwd", "description": "test"})
        assert out.startswith("{command, description}")
        assert "ls -la" not in out
        assert "/etc/passwd" not in out

    def test_empty_dict(self) -> None:
        assert redact_args({}) == "<empty args>"

    def test_none(self) -> None:
        assert redact_args(None) == "<no args>"

    def test_string_args(self) -> None:
        assert redact_args("hello").startswith("<redacted scalar")

    def test_unknown_type(self) -> None:
        assert redact_args([1, 2, 3]) == "<redacted list args>"


class TestRedactBodyPreview:
    def test_bytes_length(self) -> None:
        assert redact_body_preview(b"hello") == "<redacted body 5 bytes>"

    def test_string_length(self) -> None:
        assert redact_body_preview("12345") == "<redacted body 5 bytes>"

    def test_none(self) -> None:
        assert redact_body_preview(None) == "<redacted body none>"

    def test_does_not_include_content(self) -> None:
        secret = b'{"prompt": "personal data here"}'
        result = redact_body_preview(secret)
        assert "personal data" not in result
        assert "prompt" not in result


class TestCidSafeLogger:
    def test_stamps_marker_without_changing_message(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        base = logging.getLogger("test.toolkit.log_redaction")
        safe = get_cid_safe_logger(base)
        with caplog.at_level(logging.INFO, logger=base.name):
            safe.info("turn completed in %dms", 42)
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.getMessage() == "turn completed in 42ms"
        assert getattr(record, CID_SAFE_MARKER) is True
