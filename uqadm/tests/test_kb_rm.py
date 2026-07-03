"""Unit tests for ``uqadm kb rm`` (``cmd_rm``)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from uqadm.kb.rm import cmd_rm


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(user_id="u1", company_id="c1")


def _no_content() -> dict[str, object]:
    return {"contentInfos": [], "totalCount": 0}


def _no_folders() -> dict[str, object]:
    return {"folderInfos": [], "totalCount": 0}


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_recursive_folder_delete(
    folder: MagicMock,
    content: MagicMock,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [{"id": "c1", "key": "a.txt"}],
        "totalCount": 1,
    }
    folder.get_infos.return_value = _no_folders()

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=(),
        recursive=True,
        dry_run=False,
        assume_yes=True,
    )

    folder.delete.assert_called_once()
    kwargs = folder.delete.call_args.kwargs
    assert kwargs["scopeId"] == "scope1"
    assert kwargs["recursive"] is True
    content.delete.assert_not_called()


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_non_empty_without_recursive_refuses(
    folder: MagicMock,
    content: MagicMock,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [{"id": "c1", "key": "a.txt"}],
        "totalCount": 1,
    }
    folder.get_infos.return_value = _no_folders()

    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path="/X",
            scope_id=None,
            files=(),
            recursive=False,
            dry_run=False,
            assume_yes=True,
        )

    assert exc.value.code == 2
    folder.delete.assert_not_called()


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_empty_folder_delete_without_recursive(
    folder: MagicMock,
    content: MagicMock,
) -> None:
    # An empty folder can be removed without --recursive.
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = _no_content()
    folder.get_infos.return_value = _no_folders()

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=(),
        recursive=False,
        dry_run=False,
        assume_yes=True,
    )

    folder.delete.assert_called_once()
    assert folder.delete.call_args.kwargs["recursive"] is False


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_single_file_delete(
    folder: MagicMock,
    content: MagicMock,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [
            {"id": "c_keep", "key": "keep.txt"},
            {"id": "c_del", "key": "gone.txt"},
        ],
        "totalCount": 2,
    }

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=("gone.txt",),
        recursive=False,
        dry_run=False,
        assume_yes=True,
    )

    content.delete.assert_called_once()
    assert content.delete.call_args.kwargs["contentId"] == "c_del"
    folder.delete.assert_not_called()


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_file_delete_deletes_all_matching_keys(
    folder: MagicMock,
    content: MagicMock,
) -> None:
    # Duplicate keys in a scope are all removed.
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [
            {"id": "c_1", "key": "dup.txt"},
            {"id": "c_2", "key": "dup.txt"},
        ],
        "totalCount": 2,
    }

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=("dup.txt",),
        recursive=False,
        dry_run=False,
        assume_yes=True,
    )

    assert content.delete.call_count == 2
    deleted_ids = {call.kwargs["contentId"] for call in content.delete.call_args_list}
    assert deleted_ids == {"c_1", "c_2"}


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_missing_file_reports_and_exits_1(
    folder: MagicMock,
    content: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = _no_content()

    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path="/X",
            scope_id=None,
            files=("nope.txt",),
            recursive=False,
            dry_run=False,
            assume_yes=True,
        )

    assert exc.value.code == 1
    content.delete.assert_not_called()
    assert "not found: nope.txt" in capsys.readouterr().out


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_dry_run_all_missing_files_exits_1(
    folder: MagicMock,
    content: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A dry run that matches nothing must fail like a real run, so automation
    # using --dry-run to validate targets doesn't treat a fully missing set as
    # success.
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = _no_content()

    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path="/X",
            scope_id=None,
            files=("nope.txt",),
            recursive=False,
            dry_run=True,
            assume_yes=True,
        )

    assert exc.value.code == 1
    content.delete.assert_not_called()
    assert "not found: nope.txt" in capsys.readouterr().out


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_dry_run_folder_deletes_nothing(
    folder: MagicMock,
    content: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"

    def content_side_effect(
        user_id: str, company_id: str, **kwargs: object
    ) -> dict[str, object]:
        if kwargs.get("parentId") == "scope1":
            return {"contentInfos": [{"id": "c1", "key": "a.txt"}], "totalCount": 1}
        return _no_content()

    content.get_infos.side_effect = content_side_effect

    def folder_side_effect(
        user_id: str, company_id: str, **kwargs: object
    ) -> dict[str, object]:
        if kwargs.get("parentId") == "scope1":
            return {
                "folderInfos": [{"id": "scope_sub", "name": "sub"}],
                "totalCount": 1,
            }
        return _no_folders()

    folder.get_infos.side_effect = folder_side_effect

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=(),
        recursive=True,
        dry_run=True,
        assume_yes=True,
    )

    folder.delete.assert_not_called()
    content.delete.assert_not_called()
    out = capsys.readouterr().out
    assert "[dry-run] deleted file: a.txt" in out
    assert "[dry-run] deleted subfolder: sub" in out
    assert "[dry-run] deleted folder: /X" in out


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_dry_run_recursive_walks_nested_subtree(
    folder: MagicMock,
    content: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A recursive dry-run must list files nested in child scopes, since
    # Folder.delete(recursive=True) removes the whole subtree.
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"

    def content_side_effect(
        user_id: str, company_id: str, **kwargs: object
    ) -> dict[str, object]:
        parent = kwargs.get("parentId")
        if parent == "scope1":
            return {
                "contentInfos": [{"id": "c_top", "key": "top.txt"}],
                "totalCount": 1,
            }
        if parent == "scope_sub":
            return {
                "contentInfos": [{"id": "c_nested", "key": "nested.txt"}],
                "totalCount": 1,
            }
        return _no_content()

    content.get_infos.side_effect = content_side_effect

    def folder_side_effect(
        user_id: str, company_id: str, **kwargs: object
    ) -> dict[str, object]:
        if kwargs.get("parentId") == "scope1":
            return {
                "folderInfos": [{"id": "scope_sub", "name": "sub"}],
                "totalCount": 1,
            }
        return _no_folders()

    folder.get_infos.side_effect = folder_side_effect

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=(),
        recursive=True,
        dry_run=True,
        assume_yes=True,
    )

    folder.delete.assert_not_called()
    out = capsys.readouterr().out
    assert "[dry-run] deleted file: top.txt" in out
    assert "[dry-run] deleted file: sub/nested.txt" in out
    assert "[dry-run] deleted subfolder: sub" in out
    assert "[dry-run] deleted folder: /X" in out


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_dry_run_file_deletes_nothing(
    folder: MagicMock,
    content: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [{"id": "c_del", "key": "gone.txt"}],
        "totalCount": 1,
    }

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=("gone.txt", "missing.txt"),
        recursive=False,
        dry_run=True,
        assume_yes=True,
    )

    content.delete.assert_not_called()
    folder.delete.assert_not_called()
    out = capsys.readouterr().out
    assert "[dry-run] deleted: gone.txt" in out
    assert "not found: missing.txt" in out


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_scope_id_entry_point(
    folder: MagicMock,
    content: MagicMock,
) -> None:
    content.get_infos.return_value = _no_content()
    folder.get_infos.return_value = _no_folders()

    cmd_rm(
        _cfg(),
        folder_path=None,
        scope_id="scope_abc",
        files=(),
        recursive=True,
        dry_run=False,
        assume_yes=True,
    )

    folder.resolve_scope_id_from_folder_path.assert_not_called()
    folder.get_folder_path.assert_called_once()
    folder.delete.assert_called_once()
    assert folder.delete.call_args.kwargs["scopeId"] == "scope_abc"


def test_requires_exactly_one_target() -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path="/X",
            scope_id="scope_abc",
            files=(),
            recursive=False,
            dry_run=False,
            assume_yes=True,
        )
    assert exc.value.code == 2


def test_requires_at_least_one_target() -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path=None,
            scope_id=None,
            files=(),
            recursive=False,
            dry_run=False,
            assume_yes=True,
        )
    assert exc.value.code == 2


def test_relative_folder_path_exits_2() -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path="relative/path",
            scope_id=None,
            files=(),
            recursive=False,
            dry_run=False,
            assume_yes=True,
        )
    assert exc.value.code == 2


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_unresolvable_folder_path_exits_1(
    folder: MagicMock,
    content: MagicMock,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = None

    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path="/missing",
            scope_id=None,
            files=(),
            recursive=True,
            dry_run=False,
            assume_yes=True,
        )

    assert exc.value.code == 1
    folder.delete.assert_not_called()


@patch("uqadm.kb.rm.echo_credential_debug_if_auth_failure")
@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_invalid_scope_id_exits_1(
    folder: MagicMock,
    content: MagicMock,
    _debug: MagicMock,
) -> None:
    folder.get_folder_path.side_effect = Exception("not found")

    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path=None,
            scope_id="scope_missing",
            files=(),
            recursive=True,
            dry_run=False,
            assume_yes=True,
        )

    assert exc.value.code == 1
    content.get_infos.assert_not_called()
    folder.delete.assert_not_called()


@patch("uqadm.kb.rm.echo_credential_debug_if_auth_failure")
@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_file_delete_failure_exits_1(
    folder: MagicMock,
    content: MagicMock,
    debug: MagicMock,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [{"id": "c_del", "key": "gone.txt"}],
        "totalCount": 1,
    }
    content.delete.side_effect = RuntimeError("boom")

    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path="/X",
            scope_id=None,
            files=("gone.txt",),
            recursive=False,
            dry_run=False,
            assume_yes=True,
        )

    assert exc.value.code == 1
    content.delete.assert_called_once()
    debug.assert_called_once()


@patch("uqadm.kb.rm.typer.confirm", return_value=False)
@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_confirmation_declined_aborts(
    folder: MagicMock,
    content: MagicMock,
    _confirm: MagicMock,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = _no_content()
    folder.get_infos.return_value = _no_folders()

    with pytest.raises(SystemExit) as exc:
        cmd_rm(
            _cfg(),
            folder_path="/X",
            scope_id=None,
            files=(),
            recursive=True,
            dry_run=False,
            assume_yes=False,
        )

    assert exc.value.code == 1
    folder.delete.assert_not_called()


@patch("uqadm.kb.rm.typer.confirm", return_value=True)
@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_confirmation_accepted_deletes(
    folder: MagicMock,
    content: MagicMock,
    confirm: MagicMock,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = _no_content()
    folder.get_infos.return_value = _no_folders()

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=(),
        recursive=True,
        dry_run=False,
        assume_yes=False,
    )

    confirm.assert_called_once()
    folder.delete.assert_called_once()


@patch("uqadm.kb.rm.Content")
@patch("uqadm.kb.rm.Folder")
def test_content_pagination(
    folder: MagicMock,
    content: MagicMock,
) -> None:
    # The file matched only on the second page is still found and deleted.
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.side_effect = [
        {"contentInfos": [{"id": "c_other", "key": "other.txt"}], "totalCount": 2},
        {"contentInfos": [{"id": "c_target", "key": "target.txt"}], "totalCount": 2},
    ]

    cmd_rm(
        _cfg(),
        folder_path="/X",
        scope_id=None,
        files=("target.txt",),
        recursive=False,
        dry_run=False,
        assume_yes=True,
    )

    assert content.get_infos.call_count == 2
    content.delete.assert_called_once()
    assert content.delete.call_args.kwargs["contentId"] == "c_target"
