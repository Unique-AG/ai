"""Tests for the record of running subagent turns."""

from __future__ import annotations

from pathlib import Path

import pytest

from unique_sdk.cli.subagent_turns import (
    read_open_turns,
    record_turn_ended,
    record_turn_started,
    turns_dir_for,
)


@pytest.mark.ai
def test_turns_dir_for__sits_next_to_the_config_file(tmp_path: Path) -> None:
    turns_dir = turns_dir_for(tmp_path / ".unique-subagents.json")

    assert turns_dir == tmp_path / ".unique-subagent-turns"


@pytest.mark.ai
def test_record_turn_started__turn_is_read_back_as_open(tmp_path: Path) -> None:
    record_turn_started(tmp_path / "turns", chat_id="chat_1", message_id="msg_1")

    assert read_open_turns(tmp_path / "turns") == [
        {"chatId": "chat_1", "messageId": "msg_1"}
    ]


@pytest.mark.ai
def test_record_turn_ended__removes_only_that_turn(tmp_path: Path) -> None:
    record_turn_started(tmp_path, chat_id="chat_1", message_id="msg_1")
    record_turn_started(tmp_path, chat_id="chat_2", message_id="msg_2")

    record_turn_ended(tmp_path, message_id="msg_1")

    assert read_open_turns(tmp_path) == [{"chatId": "chat_2", "messageId": "msg_2"}]


@pytest.mark.ai
def test_record_turn_ended__unknown_turn__does_nothing(tmp_path: Path) -> None:
    record_turn_ended(tmp_path / "missing", message_id="msg_1")

    assert read_open_turns(tmp_path / "missing") == []


@pytest.mark.ai
def test_read_open_turns__skips_records_it_cannot_use(tmp_path: Path) -> None:
    record_turn_started(tmp_path, chat_id="chat_1", message_id="msg_1")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "list.json").write_text("[]", encoding="utf-8")
    (tmp_path / "no_chat.json").write_text('{"messageId": "msg_9"}', encoding="utf-8")
    (tmp_path / "msg_2.partial").write_text('{"chatId": "c"', encoding="utf-8")

    assert read_open_turns(tmp_path) == [{"chatId": "chat_1", "messageId": "msg_1"}]


@pytest.mark.ai
def test_record_turn_started__id_with_path_separator__writes_nothing(
    tmp_path: Path,
) -> None:
    turns_dir = tmp_path / "turns"

    record_turn_started(turns_dir, chat_id="chat_1", message_id="../escape")

    assert not turns_dir.exists()
    assert not (tmp_path / "escape.json").exists()


@pytest.mark.ai
def test_record_turn_started__unwritable_directory__does_not_raise(
    tmp_path: Path,
) -> None:
    blocker = tmp_path / "turns"
    blocker.write_text("a file where the directory should be", encoding="utf-8")

    record_turn_started(blocker, chat_id="chat_1", message_id="msg_1")

    assert read_open_turns(blocker) == []
