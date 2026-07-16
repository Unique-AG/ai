"""Tests for chat send/history command helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uqadm.chat.render import _sanitize
from uqadm.chat.send import _read_message_text

# --- _sanitize (control-sequence stripping) ---


def test_sanitize_passes_plain_text() -> None:
    assert _sanitize("hello world") == "hello world"


def test_sanitize_strips_sgr_color_sequence() -> None:
    assert _sanitize("\x1b[31mred text\x1b[0m") == "red text"


def test_sanitize_strips_cursor_movement() -> None:
    # ESC[2J clears screen; ESC[H homes cursor — classic overwrite attack
    assert _sanitize("\x1b[2J\x1b[H") == ""


def test_sanitize_strips_osc_window_title() -> None:
    assert _sanitize("\x1b]0;evil title\x07normal") == "normal"


def test_sanitize_strips_osc_hyperlink() -> None:
    payload = "\x1b]8;;https://evil.example\x07click me\x1b]8;;\x07"
    assert _sanitize(payload) == "click me"


def test_sanitize_strips_osc_terminated_by_st() -> None:
    assert _sanitize("\x1b]0;title\x1b\\rest") == "rest"


def test_sanitize_strips_raw_c0_controls() -> None:
    # BEL, BS, VT, FF should be stripped
    assert _sanitize("a\x07b\x08c\x0bd\x0ce") == "abcde"


def test_sanitize_strips_raw_c1_controls() -> None:
    assert _sanitize("a\x80b\x9fc") == "abc"


def test_sanitize_preserves_newlines_and_tabs() -> None:
    assert _sanitize("line1\nline2\ttabbed") == "line1\nline2\ttabbed"


def test_sanitize_normalises_crlf() -> None:
    assert _sanitize("line1\r\nline2") == "line1\nline2"


def test_sanitize_normalises_lone_cr() -> None:
    # Lone \r is a classic overwrite-previous-output attack
    assert _sanitize("real\rfake") == "real\nfake"


def test_sanitize_strips_fe_two_byte_sequence() -> None:
    # ESC c (full reset) must be stripped
    assert _sanitize("\x1bctext") == "text"


def test_sanitize_multiline_payload_with_embedded_csi() -> None:
    payload = "Safe line\n\x1b[1;32mGreen bold\x1b[0m\nAnother safe line"
    assert _sanitize(payload) == "Safe line\nGreen bold\nAnother safe line"


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


# --- cmd_history integration (with mocks) ---


def test_cmd_history_prints_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("UQADM_HOME", str(tmp_path))
    envs = tmp_path / "envs"
    envs.mkdir()
    (envs / ".qa.env").write_text(
        "UNIQUE_USER_ID=u1\nUNIQUE_COMPANY_ID=c1\n",
        encoding="utf-8",
    )

    history = [{"role": "user", "text": "hi"}]
    with patch(
        "uqadm.chat.history.load_history",
        new=MagicMock(return_value=(None, history)),
    ):
        from uqadm.chat.history import cmd_history

        cmd_history(
            "chat_1",
            slot="qa",
            max_tokens=1000,
            percent=0.5,
            max_messages=10,
            show_full=False,
            as_json=True,
            cwd=None,
        )

    out = capsys.readouterr().out
    assert '"text": "hi"' in out
