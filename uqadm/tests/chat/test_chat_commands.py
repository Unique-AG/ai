"""Tests for chat send/history command helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from uqadm.chat.send import _read_message_text


# --- send helpers ---


def test_read_message_text_from_text_arg() -> None:
    assert _read_message_text("hello", None) == "hello"


def test_read_message_text_from_file(tmp_path: Path) -> None:
    f = tmp_path / "msg.txt"
    f.write_text("from file", encoding="utf-8")
    assert _read_message_text(None, f) == "from file"


def test_read_message_text_text_wins_over_file(tmp_path: Path) -> None:
    f = tmp_path / "msg.txt"
    f.write_text("from file", encoding="utf-8")
    assert _read_message_text("from arg", f) == "from arg"


# --- cmd_send integration (with mocks) ---


def test_cmd_send_prints_reply_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir()
    env_file = envs / ".qa.env"
    env_file.write_text(
        "UNIQUE_USER_ID=u1\nUNIQUE_COMPANY_ID=c1\n",
        encoding="utf-8",
    )

    mock_result = {"text": "Hello from assistant", "chatId": "chat_1"}

    with patch(
        "uqadm.chat.send.send_message_and_wait_for_completion",
        new=AsyncMock(return_value=mock_result),
    ):
        from uqadm.chat.send import cmd_send

        cmd_send(
            "asst_1",
            slot="qa",
            text="hi",
            file=None,
            chat_id=None,
            tool_choices=None,
            poll_interval=1.0,
            max_wait=10.0,
            stop_on="stoppedStreamingAt",
            as_json=False,
            cwd=None,
        )

    out = capsys.readouterr().out
    assert "Hello from assistant" in out
