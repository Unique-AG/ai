"""Tests for unique_sdk.cli.state."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from unique_sdk.cli.config import Config
from unique_sdk.cli.state import (
    ShellState,
    _collect_filter_targets,
    _extract_target_scope_id,
)


def _folder_path_side_effect(mapping: dict[str, str]):  # type: ignore[no-untyped-def]
    """Side effect for Folder.get_folder_path mapping scope_id -> folderPath."""

    def _inner(*, user_id, company_id, scope_id):  # type: ignore[no-untyped-def]
        if scope_id in mapping:
            return {"folderPath": mapping[scope_id]}
        raise Exception(f"folder not found: {scope_id}")

    return _inner


def _content_info_side_effect(owner_map: dict[str, str]):  # type: ignore[no-untyped-def]
    """Side effect for Content.get_info mapping content_id -> ownerId scope."""

    def _inner(*, user_id, company_id, contentId):  # type: ignore[no-untyped-def]
        if contentId in owner_map:
            return {"contentInfo": [{"id": contentId, "ownerId": owner_map[contentId]}]}
        return {"contentInfo": []}

    return _inner


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


class TestShellState:
    def test_initial_state(self) -> None:
        s = ShellState(_config())
        assert s.cwd == "/"
        assert s.scope_id is None
        assert s.prompt == "/> "

    def test_cd_root(self) -> None:
        s = ShellState(_config())
        result = s.cd("/")
        assert result == "/"
        assert s.scope_id is None

    def test_cd_parent_at_root(self) -> None:
        s = ShellState(_config())
        result = s.cd("..")
        assert result == "/"

    @patch("unique_sdk.Folder.get_info")
    def test_cd_relative(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_reports"}
        s = ShellState(_config())
        result = s.cd("Reports")
        assert result == "/Reports"
        assert s.scope_id == "scope_reports"
        mock_get_info.assert_called_once_with(
            user_id="u1",
            company_id="c1",
            folderPath="/Reports",
        )

    @patch("unique_sdk.Folder.get_info")
    def test_cd_absolute(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_q1"}
        s = ShellState(_config())
        result = s.cd("/Company/Reports/Q1")
        assert result == "/Company/Reports/Q1"
        assert s.scope_id == "scope_q1"

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Folder.get_info")
    def test_cd_scope_id(self, mock_get_info, mock_get_path) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_abc"}
        mock_get_path.return_value = {"folderPath": "/Company/Reports"}
        s = ShellState(_config())
        result = s.cd("scope_abc")
        assert result == "/Company/Reports"
        assert s.scope_id == "scope_abc"

    @patch("unique_sdk.Folder.get_info")
    def test_cd_parent(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_reports"}
        s = ShellState(_config())
        s._path = "/Company/Reports/Q1"
        s._scope_id = "scope_q1"
        result = s.cd("..")
        assert result == "/Company/Reports"
        assert s.scope_id == "scope_reports"

    def test_cd_parent_to_root(self) -> None:
        s = ShellState(_config())
        s._path = "/Reports"
        s._scope_id = "scope_reports"
        result = s.cd("..")
        assert result == "/"
        assert s.scope_id is None

    def test_resolve_path_none(self) -> None:
        s = ShellState(_config())
        path, sid = s.resolve_path(None)
        assert path == "/"
        assert sid is None

    def test_resolve_path_root(self) -> None:
        s = ShellState(_config())
        path, sid = s.resolve_path("/")
        assert path == "/"
        assert sid is None

    @patch("unique_sdk.Folder.get_folder_path")
    def test_resolve_path_scope_id(self, mock_get_path) -> None:  # type: ignore[no-untyped-def]
        mock_get_path.return_value = {"folderPath": "/Reports"}
        s = ShellState(_config())
        path, sid = s.resolve_path("scope_abc")
        assert path == "/Reports"
        assert sid == "scope_abc"

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_path_absolute(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_r"}
        s = ShellState(_config())
        path, sid = s.resolve_path("/Reports")
        assert path == "/Reports"
        assert sid == "scope_r"

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_path_relative(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_q1"}
        s = ShellState(_config())
        s._path = "/Reports"
        s._scope_id = "scope_r"
        path, sid = s.resolve_path("Q1")
        assert path == "/Reports/Q1"
        assert sid == "scope_q1"

    def test_prompt_updates(self) -> None:
        s = ShellState(_config())
        assert s.prompt == "/> "
        s._path = "/Reports"
        assert s.prompt == "/Reports> "


class TestWorkspaceScopes:
    def test_no_config_file_returns_empty(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
            s = ShellState(_config())
        assert s.workspace_scope_ids == []
        assert not s.workspace_restricted

    def test_loads_scope_ids_from_config(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        (tmp_path / ".unique-search.json").write_text(  # type: ignore[union-attr]
            json.dumps({"scopeIds": ["scope_abc", "scope_def"]})
        )
        with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
            s = ShellState(_config())
        assert s.workspace_scope_ids == ["scope_abc", "scope_def"]
        assert s.workspace_restricted

    def test_loads_metadata_filter_from_config(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        rule = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "uniquepathid://scope_fund_a",
        }
        (tmp_path / ".unique-search.json").write_text(  # type: ignore[union-attr]
            json.dumps({"metaDataFilter": rule})
        )
        with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
            s = ShellState(_config())
        assert s.workspace_metadata_filter == rule

    def test_metadata_filter_none_when_absent(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        (tmp_path / ".unique-search.json").write_text(  # type: ignore[union-attr]
            json.dumps({"scopeIds": ["scope_abc"]})
        )
        with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
            s = ShellState(_config())
        assert s.workspace_metadata_filter is None

    def test_metadata_filter_ignored_when_not_dict(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        for bad in ("not-a-dict", "[]", "{}"):
            (tmp_path / ".unique-search.json").write_text(  # type: ignore[union-attr]
                json.dumps({"metaDataFilter": json.loads(bad)})
                if bad != "not-a-dict"
                else json.dumps({"metaDataFilter": bad})
            )
            with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
                s = ShellState(_config())
            assert s.workspace_metadata_filter is None, f"failed for: {bad}"

    def test_invalid_json_returns_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        (tmp_path / ".unique-search.json").write_text("not json")  # type: ignore[union-attr]
        with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
            s = ShellState(_config())
        assert s.workspace_scope_ids == []

    def test_non_dict_json_returns_empty(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """A JSON array or scalar must not crash via AttributeError."""
        for payload in ("[1, 2, 3]", '"hello"', "42", "null"):
            (tmp_path / ".unique-search.json").write_text(payload)  # type: ignore[union-attr]
            with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
                s = ShellState(_config())
            assert s.workspace_scope_ids == [], f"failed for payload: {payload}"

    def test_is_within_workspace_no_restriction(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = []
        assert s.is_within_workspace()

    def test_is_within_workspace_direct_scope_match(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = []
        s._scope_id = "scope_abc"
        assert s.is_within_workspace()

    def test_is_within_workspace_path_prefix_descendant(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = ["/Company/Reports"]
        s._path = "/Company/Reports/Q1"
        assert s.is_within_workspace()

    def test_is_within_workspace_exact_path(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = ["/Company/Reports"]
        s._path = "/Company/Reports"
        assert s.is_within_workspace()

    def test_is_within_workspace_blocked_at_root(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = ["/Company/Reports"]
        s._path = "/"
        s._scope_id = None
        assert not s.is_within_workspace()

    def test_is_within_workspace_blocked_wrong_path(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = ["/Company/Reports"]
        s._path = "/Company/Finance"
        assert not s.is_within_workspace()

    def test_root_folder_path_skipped(self) -> None:
        """A workspace scope that resolves to '/' must not be stored — it would
        make every path match via startswith('/')."""
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_root"]
        s._workspace_scope_paths = None
        with patch("unique_sdk.Folder.get_folder_path") as mock_path:
            mock_path.return_value = {"folderPath": "/"}
            paths = s._resolve_workspace_scope_paths()
        assert paths == []

    @patch("unique_sdk.Folder.get_folder_path")
    def test_resolve_workspace_scope_paths_cached(self, mock_path: patch) -> None:  # type: ignore[valid-type]
        mock_path.return_value = {"folderPath": "/Company/Reports"}
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = None
        paths1 = s._resolve_workspace_scope_paths()
        paths2 = s._resolve_workspace_scope_paths()
        assert paths1 == ["/Company/Reports"]
        assert paths2 == ["/Company/Reports"]
        mock_path.assert_called_once()


class TestFolderTargetWithinWorkspace:
    def test_no_restriction_always_allowed(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = []
        assert s.is_folder_target_within_workspace("scope_other")
        assert s.is_folder_target_within_workspace("/any/path")

    def test_scope_id_direct_match(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = []
        assert s.is_folder_target_within_workspace("scope_ws")

    @patch("unique_sdk.Folder.get_folder_path")
    def test_scope_id_descendant_allowed(self, mock_path: patch) -> None:  # type: ignore[valid-type]
        mock_path.return_value = {"folderPath": "/Workspace/Sub"}
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert s.is_folder_target_within_workspace("scope_sub")

    @patch("unique_sdk.Folder.get_folder_path")
    def test_scope_id_outside_workspace_blocked(self, mock_path: patch) -> None:  # type: ignore[valid-type]
        mock_path.return_value = {"folderPath": "/OtherTenant/Folder"}
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert not s.is_folder_target_within_workspace("scope_other")

    @patch("unique_sdk.Folder.get_folder_path")
    def test_scope_id_api_error_blocks(self, mock_path: patch) -> None:  # type: ignore[valid-type]
        mock_path.side_effect = Exception("network error")
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert not s.is_folder_target_within_workspace("scope_unknown")

    def test_absolute_path_within_workspace_allowed(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert s.is_folder_target_within_workspace("/Workspace/Sub/Deep")

    def test_absolute_path_outside_workspace_blocked(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert not s.is_folder_target_within_workspace("/OtherTenant/Folder")

    def test_absolute_path_dotdot_traversal_blocked(self) -> None:
        """/Workspace/../Evil must not pass a startswith('/Workspace/') check."""
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert not s.is_folder_target_within_workspace("/Workspace/../Evil")

    def test_relative_path_within_workspace_allowed(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        s._path = "/Workspace/Sub"
        assert s.is_folder_target_within_workspace("RelativeFolder")

    def test_relative_dotdot_traversal_blocked(self) -> None:
        """../../outside must not pass just because CWD is inside workspace."""
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        s._path = "/Workspace/Sub"
        assert not s.is_folder_target_within_workspace("../../outside")

    def test_relative_path_cwd_outside_blocked(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        s._path = "/"
        s._scope_id = None
        assert not s.is_folder_target_within_workspace("RelativeFolder")


class TestFilterTargetHelpers:
    def test_extract_scope_id_from_uniquepathid(self) -> None:
        assert (
            _extract_target_scope_id("uniquepathid://scope_root/scope_leaf")
            == "scope_leaf"
        )

    def test_extract_scope_id_from_bare(self) -> None:
        assert _extract_target_scope_id("scope_fund_a") == "scope_fund_a"

    def test_extract_scope_id_none_when_absent(self) -> None:
        assert _extract_target_scope_id("no-scope-here") is None
        assert _extract_target_scope_id(None) is None
        assert _extract_target_scope_id(123) is None

    def test_collect_targets_from_nested_tree(self) -> None:
        # Live-shaped filter: AND of (funds folders) and (folder OR contentIds).
        flt = {
            "and": [
                {
                    "or": [
                        {
                            "path": ["folderIdPath"],
                            "operator": "contains",
                            "value": "uniquepathid://scope_root/scope_fund_a",
                        },
                        {
                            "path": ["folderIdPath"],
                            "operator": "contains",
                            "value": "uniquepathid://scope_root/scope_fund_b",
                        },
                    ]
                },
                {
                    "or": [
                        {
                            "path": ["folderIdPath"],
                            "operator": "contains",
                            "value": "scope_fund_a",
                        },
                        {
                            "path": ["contentId"],
                            "operator": "in",
                            "value": ["cont_1", "cont_2"],
                        },
                    ]
                },
            ]
        }
        folder_ids, content_ids = _collect_filter_targets(flt)
        assert folder_ids == ["scope_fund_a", "scope_fund_b"]
        assert content_ids == ["cont_1", "cont_2"]


class TestMetadataFilterContentGating:
    def _state_with_filter(self, flt: dict) -> ShellState:  # type: ignore[type-arg]
        s = ShellState(_config())
        s.workspace_metadata_filter = flt
        # Avoid filesystem reads of .unique/chat-files.json in unit tests.
        s._chat_file_content_ids_cache = set()
        return s

    def test_no_filter_allows_everything(self) -> None:
        s = ShellState(_config())
        s.workspace_metadata_filter = None
        assert s.content_allowed_by_metadata_filter("cont_anything")

    def test_contentid_in_membership(self) -> None:
        s = self._state_with_filter(
            {"path": ["contentId"], "operator": "in", "value": ["cont_a", "cont_b"]}
        )
        assert s.content_allowed_by_metadata_filter("cont_a")
        assert s.content_allowed_by_metadata_filter("cont_b")
        assert not s.content_allowed_by_metadata_filter("cont_z")

    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_folderidpath_owner_inside_allowed(self, mock_path, mock_content) -> None:  # type: ignore[no-untyped-def]
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A", "scope_owner": "/Funds/Fund A/Sub"}
        )
        mock_content.side_effect = _content_info_side_effect({"cont_x": "scope_owner"})
        s = self._state_with_filter(
            {
                "path": ["folderIdPath"],
                "operator": "contains",
                "value": "uniquepathid://scope_root/scope_fund_a",
            }
        )
        assert s.content_allowed_by_metadata_filter("cont_x")

    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_folderidpath_owner_outside_denied(self, mock_path, mock_content) -> None:  # type: ignore[no-untyped-def]
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A", "scope_owner": "/Other/Folder"}
        )
        mock_content.side_effect = _content_info_side_effect({"cont_x": "scope_owner"})
        s = self._state_with_filter(
            {
                "path": ["folderIdPath"],
                "operator": "contains",
                "value": "uniquepathid://scope_root/scope_fund_a",
            }
        )
        assert not s.content_allowed_by_metadata_filter("cont_x")

    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_folderidpath_prefix_not_fooled_by_sibling(
        self, mock_path, mock_content
    ) -> None:  # type: ignore[no-untyped-def]
        # "/Funds/Fund A2" must NOT match target "/Funds/Fund A".
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A", "scope_owner": "/Funds/Fund A2"}
        )
        mock_content.side_effect = _content_info_side_effect({"cont_x": "scope_owner"})
        s = self._state_with_filter(
            {
                "path": ["folderIdPath"],
                "operator": "contains",
                "value": "scope_fund_a",
            }
        )
        assert not s.content_allowed_by_metadata_filter("cont_x")

    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_and_or_tree_contentid_branch_with_folder(
        self, mock_path, mock_content
    ) -> None:  # type: ignore[no-untyped-def]
        # AND( funds-folder , (folder OR contentId-in) ). cont_listed is in a
        # fund AND in the contentId list -> allowed.
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A", "scope_owner": "/Funds/Fund A"}
        )
        mock_content.side_effect = _content_info_side_effect(
            {"cont_listed": "scope_owner"}
        )
        flt = {
            "and": [
                {
                    "path": ["folderIdPath"],
                    "operator": "contains",
                    "value": "uniquepathid://scope_root/scope_fund_a",
                },
                {
                    "or": [
                        {
                            "path": ["folderIdPath"],
                            "operator": "contains",
                            "value": "scope_other",
                        },
                        {
                            "path": ["contentId"],
                            "operator": "in",
                            "value": ["cont_listed"],
                        },
                    ]
                },
            ]
        }
        s = self._state_with_filter(flt)
        assert s.content_allowed_by_metadata_filter("cont_listed")

    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_and_denies_when_one_branch_fails(self, mock_path, mock_content) -> None:  # type: ignore[no-untyped-def]
        # cont_listed is in the contentId list but NOT under the fund folder ->
        # AND fails (the leak the gate prevents).
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A", "scope_owner": "/Other"}
        )
        mock_content.side_effect = _content_info_side_effect(
            {"cont_listed": "scope_owner"}
        )
        flt = {
            "and": [
                {
                    "path": ["folderIdPath"],
                    "operator": "contains",
                    "value": "uniquepathid://scope_root/scope_fund_a",
                },
                {
                    "path": ["contentId"],
                    "operator": "in",
                    "value": ["cont_listed"],
                },
            ]
        }
        s = self._state_with_filter(flt)
        assert not s.content_allowed_by_metadata_filter("cont_listed")

    def test_unknown_leaf_is_non_restrictive(self) -> None:
        # A non-boundary leaf (e.g. mimeType) does not restrict locally.
        s = self._state_with_filter(
            {"path": ["mimeType"], "operator": "equals", "value": "application/pdf"}
        )
        assert s.content_allowed_by_metadata_filter("cont_anything")

    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_verdict_cached_no_repeat_api(self, mock_path, mock_content) -> None:  # type: ignore[no-untyped-def]
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A", "scope_owner": "/Funds/Fund A"}
        )
        mock_content.side_effect = _content_info_side_effect({"cont_x": "scope_owner"})
        s = self._state_with_filter(
            {
                "path": ["folderIdPath"],
                "operator": "contains",
                "value": "scope_fund_a",
            }
        )
        assert s.content_allowed_by_metadata_filter("cont_x")
        assert s.content_allowed_by_metadata_filter("cont_x")
        # Owner lookup happens once; verdict cached thereafter.
        mock_content.assert_called_once()

    def test_chat_file_exempt_from_filter(self) -> None:
        s = self._state_with_filter(
            {"path": ["contentId"], "operator": "in", "value": ["cont_a"]}
        )
        s._chat_file_content_ids_cache = {"cont_attached"}
        # Attached chat file is a turn input -> allowed even though not in filter.
        assert s.is_content_within_workspace("cont_attached")
        # A non-attached, non-listed doc is denied.
        assert not s.is_content_within_workspace("cont_other")

    def test_filter_replaces_static_scope_ids(self) -> None:
        s = self._state_with_filter(
            {"path": ["contentId"], "operator": "in", "value": ["cont_a"]}
        )
        # Static scope present but must be ignored when a filter is active.
        s.workspace_scope_ids = ["scope_broad"]
        assert s.is_content_within_workspace("cont_a")
        assert not s.is_content_within_workspace("cont_b")

    @patch("unique_sdk.Folder.get_folder_path")
    def test_metadata_filter_scope_resolves(self, mock_path) -> None:  # type: ignore[no-untyped-def]
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A"}
        )
        flt = {
            "and": [
                {
                    "path": ["folderIdPath"],
                    "operator": "contains",
                    "value": "uniquepathid://scope_root/scope_fund_a",
                },
                {
                    "path": ["contentId"],
                    "operator": "in",
                    "value": ["cont_1", "cont_2"],
                },
            ]
        }
        s = self._state_with_filter(flt)
        paths, content_ids = s.metadata_filter_scope()
        assert paths == ["/Funds/Fund A"]
        assert content_ids == ["cont_1", "cont_2"]

    @patch("unique_sdk.Folder.get_folder_path")
    def test_scope_denial_hint_with_filter(self, mock_path) -> None:  # type: ignore[no-untyped-def]
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A"}
        )
        flt = {
            "and": [
                {
                    "path": ["folderIdPath"],
                    "operator": "contains",
                    "value": "scope_fund_a",
                },
                {
                    "path": ["contentId"],
                    "operator": "in",
                    "value": ["cont_1"],
                },
            ]
        }
        s = self._state_with_filter(flt)
        hint = s.scope_denial_hint()
        assert "/Funds/Fund A" in hint
        assert "cont_1" in hint
