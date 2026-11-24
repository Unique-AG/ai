"""Tests for the records of running subagent turns."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from unique_sdk.cli.subagent_turns import (
    SubagentTurn,
    read_open_turns,
    record_turn_ended,
    record_turn_started,
)


def _turn(
    *,
    chat_id: str,
    message_id: str,
    parent_chat_id: str | None = "chat_parent",
    parent_message_id: str | None = "msg_parent",
) -> SubagentTurn:
    return {
        "version": 1,
        "chatId": chat_id,
        "messageId": message_id,
        "parentChatId": parent_chat_id,
        "parentMessageId": parent_message_id,
    }


def _start(turns_dir: Path, *, chat_id: str, message_id: str) -> None:
    record_turn_started(
        turns_dir=turns_dir,
        chat_id=chat_id,
        message_id=message_id,
        parent_chat_id="chat_parent",
        parent_message_id="msg_parent",
    )


@pytest.mark.ai
def test_record_turn_started__turn_is_read_back_with_its_parent(
    tmp_path: Path,
) -> None:
    _start(tmp_path / "turns", chat_id="chat_1", message_id="msg_1")

    assert read_open_turns(turns_dir=tmp_path / "turns") == [
        _turn(chat_id="chat_1", message_id="msg_1")
    ]


@pytest.mark.ai
def test_record_turn_started__without_parent__records_null_parent_ids(
    tmp_path: Path,
) -> None:
    record_turn_started(
        turns_dir=tmp_path,
        chat_id="chat_1",
        message_id="msg_1",
        parent_chat_id=None,
        parent_message_id=None,
    )

    assert read_open_turns(turns_dir=tmp_path) == [
        _turn(
            chat_id="chat_1",
            message_id="msg_1",
            parent_chat_id=None,
            parent_message_id=None,
        )
    ]


@pytest.mark.ai
def test_record_turn_ended__removes_only_that_turn(tmp_path: Path) -> None:
    _start(tmp_path, chat_id="chat_1", message_id="msg_1")
    _start(tmp_path, chat_id="chat_2", message_id="msg_2")

    record_turn_ended(turns_dir=tmp_path, message_id="msg_1")

    assert read_open_turns(turns_dir=tmp_path) == [
        _turn(chat_id="chat_2", message_id="msg_2")
    ]


@pytest.mark.ai
def test_record_turn_ended__unknown_turn__does_nothing(tmp_path: Path) -> None:
    record_turn_ended(turns_dir=tmp_path / "missing", message_id="msg_1")

    assert read_open_turns(turns_dir=tmp_path / "missing") == []


@pytest.mark.ai
def test_read_open_turns__skips_records_it_cannot_use_and_warns(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _start(tmp_path, chat_id="chat_1", message_id="msg_1")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "not_utf8.json").write_bytes(b'{"chatId": "\xff"}')
    (tmp_path / "list.json").write_text("[]", encoding="utf-8")
    no_version = {"chatId": "chat_9", "messageId": "msg_9"}
    (tmp_path / "no_version.json").write_text(json.dumps(no_version), encoding="utf-8")
    bad_parent = {**_turn(chat_id="chat_8", message_id="msg_8"), "parentChatId": 8}
    (tmp_path / "bad_parent.json").write_text(json.dumps(bad_parent), encoding="utf-8")
    (tmp_path / "msg_2.partial").write_text('{"chatId": "c"', encoding="utf-8")

    with caplog.at_level("WARNING"):
        turns = read_open_turns(turns_dir=tmp_path)

    assert turns == [_turn(chat_id="chat_1", message_id="msg_1")]
    assert len(caplog.records) == 5
    assert "chat_" not in caplog.text
    assert "msg_" not in caplog.text


@pytest.mark.ai
def test_record_turn_started__id_with_path_separator__writes_nothing_and_warns(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    turns_dir = tmp_path / "turns"

    with caplog.at_level("WARNING"):
        _start(turns_dir, chat_id="chat_1", message_id="../escape")

    assert not turns_dir.exists()
    assert not (tmp_path / "escape.json").exists()
    assert "not a safe file name" in caplog.text
    assert "escape" not in caplog.text


@pytest.mark.ai
def test_record_turn_started__unwritable_directory__does_not_raise(
    tmp_path: Path,
) -> None:
    blocker = tmp_path / "turns"
    blocker.write_text("a file where the directory should be", encoding="utf-8")

    _start(blocker, chat_id="chat_1", message_id="msg_1")

    assert read_open_turns(turns_dir=blocker) == []


@pytest.mark.ai
def test_record_turn_started__failed_rename__leaves_no_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail_replace(*_args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("unique_sdk.cli.subagent_turns.os.replace", _fail_replace)

    _start(tmp_path, chat_id="chat_1", message_id="msg_1")

    assert list(tmp_path.iterdir()) == []
