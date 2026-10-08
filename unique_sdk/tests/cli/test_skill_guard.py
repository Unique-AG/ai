"""Tests for the unique-cli skill write guard (UN-25784)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import unique_sdk
from unique_sdk.cli.commands.files import (
    cmd_download,
    cmd_mv_file,
    cmd_rm,
    cmd_upload,
    is_permission_denied_output,
)
from unique_sdk.cli.commands.folders import cmd_mkdir, cmd_mvdir, cmd_rmdir
from unique_sdk.cli.commands.navigation import cmd_ls
from unique_sdk.cli.commands.read import cmd_read
from unique_sdk.cli.commands.search import cmd_search
from unique_sdk.cli.config import Config
from unique_sdk.cli.skill_guard import SkillGuard, is_skill_marker_name
from unique_sdk.cli.state import ShellState

pytestmark = [pytest.mark.ai, pytest.mark.skill_guard]

# name, parent id
_FOLDERS: dict[str, tuple[str, str | None]] = {
    "scope_kb": ("Knowledge", None),
    "scope_bench": ("bench-skill-4", "scope_kb"),
    "scope_bench_refs": ("references", "scope_bench"),
    "scope_docs": ("Docs", "scope_kb"),
    "scope_home_root": ("home", None),
    "scope_my_home": ("Me", "scope_home_root"),
    "scope_my_conduct": ("skills-conduct", "scope_my_home"),
    "scope_mine_root": ("space-abc", "scope_my_conduct"),
    "scope_mine": ("my-skill", "scope_mine_root"),
    "scope_legacy_home": ("home-u1", None),
    "scope_legacy_conduct": ("skills-conduct", "scope_legacy_home"),
    "scope_legacy_space": ("space-abc", "scope_legacy_conduct"),
    "scope_legacy_mine": ("old-skill", "scope_legacy_space"),
    "scope_skills": ("skills-conduct", None),
    "scope_theirs_root": ("personal-u2", "scope_skills"),
    "scope_theirs": ("their-skill", "scope_theirs_root"),
    "scope_company": ("company-acme", "scope_skills"),
    "scope_shared": ("shared-skill", "scope_company"),
    "scope_old_personal": ("personal-u1", "scope_skills"),
    "scope_old_personal_skill": ("old-skill", "scope_old_personal"),
    "scope_lookalike_conduct": ("skills-conduct", "scope_docs"),
    "scope_lookalike_space": ("space-abc", "scope_lookalike_conduct"),
    "scope_lookalike_skill": ("fake-skill", "scope_lookalike_space"),
}

_MY_SKILL_PATH = (
    "uniquepathid://scope_home_root/scope_my_home/scope_my_conduct"
    "/scope_mine_root/scope_mine"
)

# content id, key, owner id, folderIdPath
_CONTENTS: list[tuple[str, str, str, str | None]] = [
    ("cont_bench", "SKILL.md", "scope_bench", "uniquepathid://scope_kb/scope_bench"),
    ("cont_mine", "Skills.md", "scope_mine", _MY_SKILL_PATH),
    ("cont_legacy_mine", "SKILL.md", "scope_legacy_mine", None),
    ("cont_old_personal", "SKILL.md", "scope_old_personal_skill", None),
    ("cont_lookalike", "SKILL.md", "scope_lookalike_skill", None),
    (
        "cont_theirs",
        "skill.md",
        "scope_theirs",
        "uniquepathid://scope_skills/scope_theirs_root/scope_theirs",
    ),
    ("cont_shared", "SKILL.MD", "scope_shared", None),
    (
        "cont_notes",
        "notes-skill.md",
        "scope_docs",
        "uniquepathid://scope_kb/scope_docs",
    ),
    ("cont_report", "report.pdf", "scope_docs", "uniquepathid://scope_kb/scope_docs"),
    ("cont_chat", "SKILL.md", "chat_1", None),
]


def _owner_id_filter(where: dict[str, Any]) -> list[str] | None:
    for clause in where.get("AND", []):
        owner = clause.get("ownerId")
        if owner is not None:
            return owner["in_"]
    return None


def _folder_path(scope_id: str) -> str:
    name, parent = _FOLDERS[scope_id]
    return f"{_folder_path(parent) if parent else ''}/{name}"


@dataclass
class _FakeKnowledgeBase:
    contents: list[tuple[str, str, str, str | None]] = field(
        default_factory=lambda: list(_CONTENTS)
    )
    search: MagicMock = field(default_factory=MagicMock)
    folder_get_info: MagicMock = field(default_factory=MagicMock)

    include_owner_id: bool = True

    def search_results(self, **kwargs: Any) -> list[dict[str, Any]]:
        owner_ids = _owner_id_filter(kwargs["where"])
        return [
            {
                "id": content_id,
                "key": key,
                **({"ownerId": owner_id} if self.include_owner_id else {}),
                "metadata": {"folderIdPath": folder_id_path} if folder_id_path else {},
            }
            for content_id, key, owner_id, folder_id_path in self.contents
            if key.lower().endswith(("skill.md", "skills.md"))
            and (owner_ids is None or owner_id in owner_ids)
        ]

    def folder_info(self, **params: Any) -> dict[str, Any]:
        scope_id = params.get("scopeId")
        if scope_id is None:
            by_path = {_folder_path(sid): sid for sid in _FOLDERS}
            scope_id = by_path.get(params.get("folderPath", ""))
        if scope_id not in _FOLDERS:
            raise unique_sdk.UniqueError("folder not found")
        name, parent = _FOLDERS[scope_id]
        return {"id": scope_id, "name": name, "parentId": parent}

    def content_info(self, **params: Any) -> dict[str, Any]:
        for content_id, key, owner_id, _ in self.contents:
            if content_id == params.get("contentId"):
                return {
                    "contentInfo": [
                        {
                            "id": content_id,
                            "key": key,
                            "title": key,
                            "ownerId": owner_id,
                        }
                    ]
                }
        return {"contentInfo": []}


@pytest.fixture
def kb() -> Iterator[_FakeKnowledgeBase]:
    fake = _FakeKnowledgeBase()
    fake.search.side_effect = fake.search_results
    fake.folder_get_info.side_effect = lambda **kwargs: fake.folder_info(**kwargs)
    with (
        patch.object(unique_sdk.Content, "search", fake.search),
        patch.object(unique_sdk.Folder, "get_info", fake.folder_get_info),
        patch.object(
            unique_sdk.Content,
            "get_info",
            side_effect=lambda **kwargs: fake.content_info(**kwargs),
        ),
        patch.object(
            unique_sdk.Folder,
            "get_folder_path",
            side_effect=lambda **kwargs: {
                "folderPath": _folder_path(kwargs["scope_id"])
            },
        ),
    ):
        yield fake


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


def _state(path: str = "/", scope_id: str | None = None) -> ShellState:
    state = ShellState(_config())
    state._path = path
    state._scope_id = scope_id
    return state


class TestIsSkillMarkerName:
    @pytest.mark.parametrize(
        "name",
        ["SKILL.md", "skill.md", "Skills.MD", "folder/skills.md", " SKILL.md "],
    )
    def test_markers(self, name: str) -> None:
        assert is_skill_marker_name(name)

    @pytest.mark.parametrize(
        "name", ["notes-skill.md", "skill.txt", "SKILL.md.bak", "skillset.md", ""]
    )
    def test_non_markers(self, name: str) -> None:
        assert not is_skill_marker_name(name)


class TestFolderWrites:
    @pytest.mark.parametrize(
        ("scope_id", "denied"),
        [
            ("scope_bench", True),
            ("scope_bench_refs", True),
            ("scope_theirs", True),
            ("scope_shared", True),
            ("scope_old_personal_skill", True),
            ("scope_lookalike_skill", True),
            ("scope_mine", False),
            ("scope_legacy_mine", False),
            ("scope_docs", False),
            ("scope_kb", False),
        ],
    )
    def test_skill_at_or_above_folder(
        self, kb: _FakeKnowledgeBase, scope_id: str, denied: bool
    ) -> None:
        assert SkillGuard(_config()).is_folder_write_denied(scope_id) is denied

    @pytest.mark.parametrize(
        ("scope_id", "denied"),
        [
            ("scope_kb", True),
            ("scope_skills", True),
            ("scope_company", True),
            ("scope_old_personal", True),
            ("scope_my_home", True),
            ("scope_mine_root", False),
        ],
    )
    def test_skill_below_folder(
        self, kb: _FakeKnowledgeBase, scope_id: str, denied: bool
    ) -> None:
        guard = SkillGuard(_config())
        assert guard.is_folder_write_denied(scope_id, include_subtree=True) is denied

    @pytest.mark.parametrize(
        ("scope_id", "file_name", "denied"),
        [
            ("scope_docs", "SKILL.md", True),
            ("scope_docs", "skills.MD", True),
            ("scope_docs", "notes.md", False),
            ("scope_mine_root", "SKILL.md", False),
        ],
    )
    def test_creating_a_marker(
        self, kb: _FakeKnowledgeBase, scope_id: str, file_name: str, denied: bool
    ) -> None:
        guard = SkillGuard(_config())
        assert guard.is_folder_write_denied(scope_id, new_file_name=file_name) is denied

    def test_unknown_folder_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        guard = SkillGuard(_config())
        assert guard.is_folder_write_denied(None)
        assert guard.is_folder_write_denied("scope_missing")

    def test_failed_marker_search_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        kb.search.side_effect = unique_sdk.UniqueError("search failed")
        assert SkillGuard(_config()).is_folder_write_denied("scope_docs")

    def test_personal_skills_need_no_marker_search(
        self, kb: _FakeKnowledgeBase
    ) -> None:
        assert not SkillGuard(_config()).is_folder_write_denied("scope_mine")
        kb.search.assert_not_called()

    @pytest.mark.parametrize(
        "scope_id", ["scope_old_personal", "scope_lookalike_space"]
    )
    def test_space_or_personal_folder_outside_a_home_is_not_personal(
        self, kb: _FakeKnowledgeBase, scope_id: str
    ) -> None:
        guard = SkillGuard(_config())
        assert guard.is_folder_write_denied(scope_id, new_file_name="SKILL.md")

    def test_legacy_home_of_another_user_is_not_personal(
        self, kb: _FakeKnowledgeBase
    ) -> None:
        config = Config(
            user_id="u2",
            company_id="c1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
        )
        assert SkillGuard(config).is_folder_write_denied("scope_legacy_mine")

    def test_folder_write_searches_only_the_folder_chain(
        self, kb: _FakeKnowledgeBase
    ) -> None:
        SkillGuard(_config()).is_folder_write_denied("scope_docs")
        assert kb.search.call_count == 1
        where = kb.search.call_args.kwargs["where"]
        assert _owner_id_filter(where) == ["scope_docs", "scope_kb"]

    def test_company_wide_markers_are_searched_once_per_process(
        self, kb: _FakeKnowledgeBase
    ) -> None:
        guard = SkillGuard(_config())
        guard.is_folder_write_denied("scope_docs", include_subtree=True)
        guard.is_folder_write_denied("scope_kb", include_subtree=True)
        company_wide = [
            call
            for call in kb.search.call_args_list
            if _owner_id_filter(call.kwargs["where"]) is None
        ]
        assert len(company_wide) == 1

    def test_chat_marker_with_folder_id_path_is_not_a_skill(
        self, kb: _FakeKnowledgeBase
    ) -> None:
        kb.contents = [
            ("cont_chat", "SKILL.md", "chat_1", "uniquepathid://scope_kb/scope_docs")
        ]
        guard = SkillGuard(_config())
        assert not guard.is_folder_write_denied("scope_kb", include_subtree=True)

    def test_subtree_check_uses_folder_id_path_without_owner_id(
        self, kb: _FakeKnowledgeBase
    ) -> None:
        kb.include_owner_id = False
        guard = SkillGuard(_config())
        assert guard.is_folder_write_denied("scope_kb", include_subtree=True)


class TestReads:
    @pytest.mark.parametrize(
        ("scope_id", "hidden"),
        [
            ("scope_bench", True),
            ("scope_bench_refs", True),
            ("scope_theirs", True),
            ("scope_shared", True),
            ("scope_old_personal_skill", True),
            ("scope_lookalike_skill", True),
            ("scope_mine", False),
            ("scope_mine_root", False),
            ("scope_legacy_mine", False),
            ("scope_docs", False),
            ("scope_kb", False),
        ],
    )
    def test_folder_hidden_inside_skills(
        self, kb: _FakeKnowledgeBase, scope_id: str, hidden: bool
    ) -> None:
        assert SkillGuard(_config()).is_folder_hidden(scope_id) is hidden

    def test_unknown_folder_is_hidden(self, kb: _FakeKnowledgeBase) -> None:
        assert SkillGuard(_config()).is_folder_hidden("scope_missing")

    def test_failed_marker_search_hides_the_path(self, kb: _FakeKnowledgeBase) -> None:
        kb.search.side_effect = unique_sdk.UniqueError("search failed")
        assert SkillGuard(_config()).is_folder_path_hidden(["scope_kb", "scope_docs"])

    def test_plain_path_checks_no_folder_chain(self, kb: _FakeKnowledgeBase) -> None:
        guard = SkillGuard(_config())
        assert not guard.is_folder_path_hidden(["scope_kb", "scope_docs"])
        kb.folder_get_info.assert_not_called()


class TestPathWrites:
    @pytest.mark.parametrize(
        ("path", "denied"),
        [
            ("/Knowledge/bench-skill-4/new", True),
            ("/Knowledge/bench-skill-4/references/a/b", True),
            ("/Knowledge/Docs/new/deeper", False),
            ("/home/Me/skills-conduct/space-abc/my-skill/assets", False),
            ("/skills-conduct/personal-u1/old-skill/assets", True),
            ("/Nowhere/new", False),
        ],
    )
    def test_nearest_existing_folder_decides(
        self, kb: _FakeKnowledgeBase, path: str, denied: bool
    ) -> None:
        assert SkillGuard(_config()).is_path_write_denied(path) is denied


class TestCommands:
    def test_upload_into_skill_is_denied(
        self, kb: _FakeKnowledgeBase, tmp_path: Path
    ) -> None:
        local = tmp_path / "SKILL.md"
        local.write_text("changed")
        with patch("unique_sdk.cli.commands.files.upload_file") as upload:
            out = cmd_upload(_state(), str(local), "scope_bench")
        assert is_permission_denied_output(out)
        assert "outside your personal skills" in out
        upload.assert_not_called()

    def test_upload_marker_into_plain_folder_is_denied(
        self, kb: _FakeKnowledgeBase, tmp_path: Path
    ) -> None:
        local = tmp_path / "SKILL.md"
        local.write_text("new skill")
        with patch("unique_sdk.cli.commands.files.upload_file") as upload:
            out = cmd_upload(_state(), str(local), "scope_docs")
        assert is_permission_denied_output(out)
        upload.assert_not_called()

    def test_upload_into_plain_folder_is_allowed(
        self, kb: _FakeKnowledgeBase, tmp_path: Path
    ) -> None:
        local = tmp_path / "report.md"
        local.write_text("report")
        with patch("unique_sdk.cli.commands.files.upload_file") as upload:
            upload.return_value = MagicMock(id="cont_new")
            out = cmd_upload(_state(), str(local), "scope_docs")
        assert out.startswith("Uploaded: report.md (cont_new)")

    def test_rm_skill_file_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        with patch.object(unique_sdk.Content, "delete") as delete:
            out = cmd_rm(_state(), "cont_bench")
        assert is_permission_denied_output(out)
        delete.assert_not_called()

    def test_rm_own_personal_skill_file_is_allowed(
        self, kb: _FakeKnowledgeBase
    ) -> None:
        with patch.object(unique_sdk.Content, "delete") as delete:
            out = cmd_rm(_state(), "cont_mine")
        assert out.startswith("Deleted:")
        delete.assert_called_once()

    def test_rm_chat_owned_file_is_allowed(self, kb: _FakeKnowledgeBase) -> None:
        with patch.object(unique_sdk.Content, "delete") as delete:
            out = cmd_rm(_state(), "cont_chat")
        assert out.startswith("Deleted:")
        delete.assert_called_once()

    def test_mv_file_into_marker_name_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        with patch.object(unique_sdk.Content, "update") as update:
            out = cmd_mv_file(_state(), "cont_report", "SKILL.md")
        assert is_permission_denied_output(out)
        update.assert_not_called()

    def test_mkdir_inside_skill_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        with patch.object(unique_sdk.Folder, "create_paths") as create:
            out = cmd_mkdir(
                _state("/Knowledge/bench-skill-4", "scope_bench"), "scripts"
            )
        assert is_permission_denied_output(out)
        create.assert_not_called()

    def test_rmdir_above_skill_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        with patch.object(unique_sdk.Folder, "delete") as delete:
            out = cmd_rmdir(_state(), "scope_kb", recursive=True)
        assert is_permission_denied_output(out)
        delete.assert_not_called()

    def test_mvdir_own_personal_skill_is_allowed(self, kb: _FakeKnowledgeBase) -> None:
        with patch.object(unique_sdk.Folder, "update") as update:
            update.return_value = {"id": "scope_mine", "name": "renamed"}
            out = cmd_mvdir(_state(), "scope_mine", "renamed")
        assert out.startswith("Renamed folder")


def _hit(content_id: str, folder_id_path: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=content_id,
        key=f"{content_id}.md",
        title=content_id,
        text="text",
        metadata={"folderIdPath": folder_id_path} if folder_id_path else None,
    )


class TestReadCommands:
    def test_search_drops_hits_inside_protected_skills(
        self, kb: _FakeKnowledgeBase, tmp_path: Path
    ) -> None:
        hits = [
            _hit("cont_bench", "uniquepathid://scope_kb/scope_bench"),
            _hit(
                "cont_theirs",
                "uniquepathid://scope_skills/scope_theirs_root/scope_theirs",
            ),
            _hit("cont_shared", None),
            _hit("cont_mine", _MY_SKILL_PATH),
            _hit("cont_report", "uniquepathid://scope_kb/scope_docs"),
        ]
        with patch.object(unique_sdk.Search, "create", return_value=hits):
            out = cmd_search(_state(), "query", refs_log_path=tmp_path / "refs.jsonl")
        assert "Found 2 result(s)" in out
        assert "cont_mine" in out
        assert "cont_report" in out
        assert "cont_bench" not in out
        assert "cont_theirs" not in out
        assert "cont_shared" not in out

    def test_read_skill_file_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        out = cmd_read(_state(), "cont_bench")
        assert out.startswith("read: permission denied")
        assert "outside your personal skills" in out

    def test_read_own_personal_skill_file_is_allowed(
        self, kb: _FakeKnowledgeBase
    ) -> None:
        assert not cmd_read(_state(), "cont_mine").startswith("read: permission denied")

    def test_download_skill_file_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        with patch("unique_sdk.cli.commands.files.download_content") as download:
            out = cmd_download(_state(), "cont_theirs")
        assert is_permission_denied_output(out)
        download.assert_not_called()

    def test_ls_inside_skill_is_denied(self, kb: _FakeKnowledgeBase) -> None:
        out = cmd_ls(_state("/Knowledge/bench-skill-4", "scope_bench"))
        assert out.startswith("ls: permission denied")

    @pytest.mark.parametrize("include_owner_id", [True, False])
    def test_ls_hides_skill_child_folders(
        self, kb: _FakeKnowledgeBase, include_owner_id: bool
    ) -> None:
        kb.include_owner_id = include_owner_id
        children = [
            {"id": "scope_bench", "name": "bench-skill-4"},
            {"id": "scope_docs", "name": "Docs"},
        ]
        with (
            patch.object(
                unique_sdk.Folder,
                "get_infos",
                return_value={"folderInfos": children, "totalCount": 2},
            ),
            patch.object(
                unique_sdk.Content,
                "get_infos",
                return_value={"contentInfos": [], "totalCount": 0},
            ),
        ):
            out = cmd_ls(_state("/Knowledge", "scope_kb"))
        assert "Docs" in out
        assert "bench-skill-4" not in out
        assert "1 folder(s)" in out
