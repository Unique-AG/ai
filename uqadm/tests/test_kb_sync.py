"""Unit tests for ``uqadm kb sync`` (``cmd_sync``)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from unique_sdk import InvalidRequestError

from uqadm.kb.sync import cmd_sync


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(user_id="u1", company_id="c1")


def _no_remote() -> dict[str, object]:
    return {"contentInfos": [], "totalCount": 0}


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_new_file_uploaded(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = _no_remote()

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=False,
    )

    upload.assert_called_once()
    args, kwargs = upload.call_args
    assert args[3] == "a.txt"  # displayed_filename / key
    assert kwargs["scope_or_unique_path"] == "scope1"


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_existing_file_replaced(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [{"key": "a.txt"}],
        "totalCount": 1,
    }

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=False,
    )

    # Replaced files are still re-uploaded (upsert overwrites by key).
    upload.assert_called_once()


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_non_recursive_ignores_subdirs(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "top.txt").write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("y", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = _no_remote()

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=False,
    )

    upload.assert_called_once()
    assert upload.call_args.args[3] == "top.txt"


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_recursive_mirrors_subdirs(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "top.txt").write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("y", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = _no_remote()

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=True,
        dry_run=False,
    )

    assert upload.call_count == 2
    resolved_paths = {
        call.kwargs["folder_path"]
        for call in folder.resolve_scope_id_from_folder_path_with_create.call_args_list
    }
    assert resolved_paths == {"/X", "/X/sub"}


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_scope_id_resolved_via_get_folder_path(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    folder.get_folder_path.return_value = {"folderPath": "/Base"}
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = _no_remote()

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path=None,
        scope_id="scope_abc",
        recursive=False,
        dry_run=False,
    )

    folder.get_folder_path.assert_called_once()
    assert (
        folder.resolve_scope_id_from_folder_path_with_create.call_args.kwargs[
            "folder_path"
        ]
        == "/Base"
    )
    upload.assert_called_once()


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_dry_run_uploads_nothing(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = _no_remote()

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=True,
    )

    upload.assert_not_called()
    folder.resolve_scope_id_from_folder_path_with_create.assert_not_called()


def test_requires_exactly_one_target(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_sync(
            _cfg(),
            local_dir=tmp_path,
            folder_path="/X",
            scope_id="scope_abc",
            recursive=False,
            dry_run=False,
        )
    assert exc.value.code == 2


def test_requires_at_least_one_target(tmp_path: Path) -> None:
    # The other half of the mutual-exclusion check: neither target given.
    with pytest.raises(SystemExit) as exc:
        cmd_sync(
            _cfg(),
            local_dir=tmp_path,
            folder_path=None,
            scope_id=None,
            recursive=False,
            dry_run=False,
        )
    assert exc.value.code == 2


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_empty_dir_is_noop(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    # No files: bail out before touching the SDK.
    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=False,
    )

    upload.assert_not_called()
    folder.resolve_scope_id_from_folder_path_with_create.assert_not_called()
    content.get_infos.assert_not_called()


@patch("uqadm.kb.sync.mimetypes.guess_type", return_value=(None, None))
@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_unknown_mime_fails_upload(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    _guess_type: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A file whose MIME type cannot be determined is not uploaded; it counts as
    # failed and the command exits 1.
    (tmp_path / "noext").write_text("x", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = _no_remote()

    with pytest.raises(SystemExit) as exc:
        cmd_sync(
            _cfg(),
            local_dir=tmp_path,
            folder_path="/X",
            scope_id=None,
            recursive=False,
            dry_run=False,
        )

    assert exc.value.code == 1
    upload.assert_not_called()
    assert "failed: noext: could not determine MIME type" in capsys.readouterr().err


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_md_uploads_as_text_markdown(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "readme.md").write_text("# hi", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = _no_remote()

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=False,
    )

    upload.assert_called_once()
    assert upload.call_args.args[4] == "text/markdown"


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_xsd_uploads_as_application_xml(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "schema.xsd").write_text("<xsd/>", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = _no_remote()

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=False,
    )

    upload.assert_called_once()
    assert upload.call_args.args[4] == "application/xml"


@patch("uqadm.kb.sync.echo_credential_debug_if_auth_failure")
@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_upload_failure_counts_and_exits_1(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    debug: MagicMock,
    tmp_path: Path,
) -> None:
    # A failed upload is reported, surfaces the auth-debug hook, and exits 1.
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.return_value = _no_remote()
    upload.side_effect = RuntimeError("boom")

    with pytest.raises(SystemExit) as exc:
        cmd_sync(
            _cfg(),
            local_dir=tmp_path,
            folder_path="/X",
            scope_id=None,
            recursive=False,
            dry_run=False,
        )

    assert exc.value.code == 1
    upload.assert_called_once()
    debug.assert_called_once()


@patch("uqadm.kb.sync.echo_credential_debug_if_auth_failure")
@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_scope_id_resolution_failure_exits_1(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    _debug: MagicMock,
    tmp_path: Path,
) -> None:
    # Failing to resolve a --scope-id to a path aborts before any upload.
    folder.get_folder_path.side_effect = RuntimeError("nope")

    with pytest.raises(SystemExit) as exc:
        cmd_sync(
            _cfg(),
            local_dir=tmp_path,
            folder_path=None,
            scope_id="scope_abc",
            recursive=False,
            dry_run=False,
        )

    assert exc.value.code == 1
    upload.assert_not_called()


@patch("uqadm.kb.sync.echo_credential_debug_if_auth_failure")
@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_folder_resolve_failure_counts_group_failed(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    debug: MagicMock,
    tmp_path: Path,
) -> None:
    # A folder that fails to resolve marks its whole group as failed (exit 1)
    # without uploading or listing remote keys.
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.side_effect = RuntimeError(
        "denied"
    )

    with pytest.raises(SystemExit) as exc:
        cmd_sync(
            _cfg(),
            local_dir=tmp_path,
            folder_path="/X",
            scope_id=None,
            recursive=False,
            dry_run=False,
        )

    assert exc.value.code == 1
    upload.assert_not_called()
    content.get_infos.assert_not_called()
    debug.assert_called_once()


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_dry_run_missing_folder_treats_files_as_new(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # On a dry run the target folder may not exist yet; the SDK raises
    # InvalidRequestError, which is swallowed so files show as "new" and no
    # remote listing happens.
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path.side_effect = InvalidRequestError(
        "not found", params=None
    )

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=True,
    )

    upload.assert_not_called()
    content.get_infos.assert_not_called()
    folder.resolve_scope_id_from_folder_path_with_create.assert_not_called()
    assert "[dry-run] new: a.txt" in capsys.readouterr().out


@patch("uqadm.kb.sync.upload_file")
@patch("uqadm.kb.sync.Content")
@patch("uqadm.kb.sync.Folder")
def test_remote_keys_paginates(
    folder: MagicMock,
    content: MagicMock,
    upload: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Remote keys are collected across multiple pages; a key found only on the
    # second page must still mark the local file as "replaced".
    (tmp_path / "b.txt").write_text("hi", encoding="utf-8")
    folder.resolve_scope_id_from_folder_path_with_create.return_value = "scope1"
    content.get_infos.side_effect = [
        {"contentInfos": [{"key": "other.txt"}], "totalCount": 2},
        {"contentInfos": [{"key": "b.txt"}], "totalCount": 2},
    ]

    cmd_sync(
        _cfg(),
        local_dir=tmp_path,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=False,
    )

    assert content.get_infos.call_count == 2
    assert content.get_infos.call_args_list[0].kwargs["skip"] == 0
    assert content.get_infos.call_args_list[1].kwargs["skip"] == 1
    upload.assert_called_once()
    assert "replaced: b.txt" in capsys.readouterr().out
