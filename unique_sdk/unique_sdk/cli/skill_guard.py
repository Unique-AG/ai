"""Keep CLI reads and writes out of skill folders (a ``skill.md``/``skills.md`` marker
at or above the folder) outside the caller's personal skills
(``<home>/skills-conduct/space-<spaceId>``). Conduct loads the skills a turn may use
into the workspace, so the agent never needs them from the knowledge base."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import unique_sdk
from unique_sdk.cli.config import Config

_MARKER_NAME_RE = re.compile(r"^skills?\.md$", re.IGNORECASE)

# The SDK JSON-encodes request params without an Enum encoder, so
# ``mode: insensitive`` can't be sent. Match the common spellings instead and
# re-check every hit with ``is_skill_marker_name``.
_MARKER_KEY_SUFFIXES = tuple(
    f"{stem}{extension}"
    for stem in ("skill", "Skill", "SKILL", "skills", "Skills", "SKILLS")
    for extension in (".md", ".MD")
)

_FOLDER_ID_PATH_PREFIX = "uniquepathid://"
_MAX_FOLDER_DEPTH = 64

# Same names as Conduct's ``conduct/contract/user_home.py`` and node-ingestion.
_PERSONAL_SKILLS_FOLDER_NAME = "skills-conduct"
_PERSONAL_SKILLS_SPACE_PREFIX = "space-"
_USER_HOME_ROOT_NAME = "home"
_LEGACY_USER_HOME_PREFIX = "home-"


def is_skill_marker_name(name: str) -> bool:
    """True when the last segment of *name* is a skill marker file name."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return bool(_MARKER_NAME_RE.match(base))


def skill_write_denial(command: str, target: str) -> str:
    """Denial text in the ``<command>: permission denied`` shape the CLI exits on."""
    return (
        f"{command}: permission denied: {target} is part of a skill outside your "
        "personal skills, or its skill status could not be checked. Change skills "
        "only with the create-skill or edit-skill skills."
    )


def skill_read_denial(command: str, target: str) -> str:
    """Denial text in the ``<command>: permission denied`` shape the CLI exits on."""
    return (
        f"{command}: permission denied: {target} is part of a skill outside your "
        "personal skills, or its skill status could not be checked. The skills "
        "you can use are already in your workspace."
    )


@dataclass(frozen=True)
class _FolderNode:
    scope_id: str
    name: str
    parent_id: str | None


@dataclass(frozen=True)
class _SkillMarker:
    skill_folder_id: str
    # Empty when the content has no ``folderIdPath``; looked up on demand.
    folder_ids: frozenset[str]


class SkillGuard:
    """Answers whether a read or write would touch a protected skill."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._folders: dict[str, _FolderNode] = {}
        self._markers: tuple[_SkillMarker, ...] | None = None
        self._hidden: dict[str, bool] = {}

    def is_folder_hidden(self, scope_id: str) -> bool:
        """True when *scope_id* is inside a protected skill. Fails closed."""
        cached = self._hidden.get(scope_id)
        if cached is not None:
            return cached
        try:
            chain = self._folder_chain(scope_id)
            hidden = not self._is_in_own_personal_layer(chain) and self._has_marker_in(
                [node.scope_id for node in chain]
            )
        except unique_sdk.UniqueError:
            hidden = True
        self._hidden[scope_id] = hidden
        return hidden

    def is_folder_path_hidden(self, folder_ids: Sequence[str]) -> bool:
        """True when a ``folderIdPath`` runs through a protected skill. Fails closed."""
        try:
            skill_folder_ids = {
                marker.skill_folder_id for marker in self._all_skill_markers()
            }
        except unique_sdk.UniqueError:
            return True
        return any(
            self.is_folder_hidden(folder_id)
            for folder_id in folder_ids
            if folder_id in skill_folder_ids
        )

    def visible_child_folders(self, folders: Sequence[Any]) -> list[Any]:
        """Drop protected skills from the child folders of a visible folder."""
        folder_ids = [folder.get("id") for folder in folders if folder.get("id")]
        if not folder_ids:
            return list(folders)
        skill_folder_ids = {
            _marker_owner_id(content)
            for content in self._search_markers({"ownerId": {"in_": folder_ids}})
            if is_skill_marker_name(content.get("key") or "")
        }
        return [
            folder
            for folder in folders
            if folder.get("id") not in skill_folder_ids
            or not self.is_folder_hidden(folder["id"])
        ]

    def is_folder_write_denied(
        self,
        scope_id: str | None,
        *,
        include_subtree: bool = False,
        new_file_name: str | None = None,
    ) -> bool:
        """True when writing in *scope_id* would change a protected skill.

        ``include_subtree`` also protects skills below the folder (``rmdir``,
        ``mvdir``). ``new_file_name`` protects against creating a marker, which
        would turn the folder into a skill. Fails closed when the folder is
        unknown or a lookup fails.
        """
        if not scope_id:
            return True
        try:
            return self._is_folder_write_denied(
                scope_id,
                include_subtree=include_subtree,
                new_file_name=new_file_name,
            )
        except unique_sdk.UniqueError:
            return True

    def is_path_write_denied(self, folder_path: str) -> bool:
        """True when creating *folder_path* would add structure inside a protected skill.

        Checks the deepest existing folder on the path, because the target does
        not exist yet.
        """
        segments = [segment for segment in folder_path.split("/") if segment]
        while segments:
            candidate = "/" + "/".join(segments)
            try:
                info = unique_sdk.Folder.get_info(
                    user_id=self._config.user_id,
                    company_id=self._config.company_id,
                    folderPath=candidate,
                )
            except unique_sdk.UniqueError:
                segments.pop()
                continue
            scope_id = info.get("id")
            if not scope_id:
                return True
            return self.is_folder_write_denied(scope_id)
        return False

    def _is_folder_write_denied(
        self,
        scope_id: str,
        *,
        include_subtree: bool,
        new_file_name: str | None,
    ) -> bool:
        chain = self._folder_chain(scope_id)
        if self._is_in_own_personal_layer(chain):
            return False
        if new_file_name is not None and is_skill_marker_name(new_file_name):
            return True
        if self._has_marker_in([node.scope_id for node in chain]):
            return True
        if include_subtree:
            return any(
                scope_id in self._marker_folder_ids(marker)
                for marker in self._all_skill_markers()
            )
        return False

    def _is_in_own_personal_layer(self, chain: list[_FolderNode]) -> bool:
        """True inside ``<home>/skills-conduct/space-<spaceId>``.

        node-ingestion resolves no other user's home for the caller, so a home in
        the chain is the caller's own. node-ingestion re-checks the owner on write.
        """
        return any(
            node.name.startswith(_PERSONAL_SKILLS_SPACE_PREFIX)
            and len(chain) > index + 2
            and chain[index + 1].name == _PERSONAL_SKILLS_FOLDER_NAME
            and self._is_own_home(chain[index + 2 :])
            for index, node in enumerate(chain)
        )

    def _is_own_home(self, chain_from_home: list[_FolderNode]) -> bool:
        """``/home/<UserName>``, or the legacy root ``/home-<userId>``."""
        home, *above = chain_from_home
        if not above:
            return home.name == f"{_LEGACY_USER_HOME_PREFIX}{self._config.user_id}"
        return (
            len(above) == 1
            and above[0].name == _USER_HOME_ROOT_NAME
            and above[0].parent_id is None
        )

    def _has_marker_in(self, folder_ids: list[str]) -> bool:
        if not folder_ids:
            return False
        results = self._search_markers({"ownerId": {"in_": folder_ids}})
        return any(
            is_skill_marker_name(content.get("key") or "") for content in results
        )

    def _marker_folder_ids(self, marker: _SkillMarker) -> frozenset[str]:
        if marker.folder_ids:
            return marker.folder_ids
        return frozenset(
            node.scope_id for node in self._folder_chain(marker.skill_folder_id)
        )

    def _folder_chain(self, scope_id: str) -> list[_FolderNode]:
        """The folder and its ancestors, nearest first."""
        chain: list[_FolderNode] = []
        current: str | None = scope_id
        while current and len(chain) < _MAX_FOLDER_DEPTH:
            node = self._folder(current)
            chain.append(node)
            current = node.parent_id
        return chain

    def _folder(self, scope_id: str) -> _FolderNode:
        cached = self._folders.get(scope_id)
        if cached is not None:
            return cached
        info = unique_sdk.Folder.get_info(
            user_id=self._config.user_id,
            company_id=self._config.company_id,
            scopeId=scope_id,
        )
        node = _FolderNode(
            scope_id=info["id"],
            name=info.get("name") or "",
            parent_id=info.get("parentId"),
        )
        self._folders[scope_id] = node
        return node

    def _search_markers(
        self, where: unique_sdk.Content.ContentWhereInput | None = None
    ) -> list[unique_sdk.Content]:
        key_filter: unique_sdk.Content.ContentWhereInput = {
            "OR": [{"key": {"endsWith": suffix}} for suffix in _MARKER_KEY_SUFFIXES]
        }
        clauses = [key_filter] if where is None else [key_filter, where]
        return unique_sdk.Content.search(
            user_id=self._config.user_id,
            company_id=self._config.company_id,
            where={"AND": clauses},
        )

    def _all_skill_markers(self) -> tuple[_SkillMarker, ...]:
        """Every marker the caller can read. Only subtree checks need this."""
        if self._markers is not None:
            return self._markers
        markers: list[_SkillMarker] = []
        for content in self._search_markers():
            if not is_skill_marker_name(content.get("key") or ""):
                continue
            path_ids = folder_ids_from_metadata(content.get("metadata"))
            owner_id = _marker_owner_id(content)
            if not owner_id.startswith("scope_"):
                continue
            markers.append(
                _SkillMarker(
                    skill_folder_id=owner_id,
                    folder_ids=frozenset({owner_id, *path_ids})
                    if path_ids
                    else frozenset(),
                )
            )
        self._markers = tuple(markers)
        return self._markers


def _marker_owner_id(content: unique_sdk.Content) -> str:
    """The marker's folder: ``ownerId``, else the last ``folderIdPath`` segment."""
    path_ids = folder_ids_from_metadata(content.get("metadata"))
    return content.get("ownerId") or (path_ids[-1] if path_ids else "")


def folder_ids_from_metadata(metadata: object) -> list[str]:
    """Folder ids in a content's ``folderIdPath``, or ``[]`` when absent."""
    if not isinstance(metadata, dict):
        return []
    folder_id_path = metadata.get("folderIdPath")
    if not isinstance(folder_id_path, str):
        return []
    path = folder_id_path.removeprefix(_FOLDER_ID_PATH_PREFIX)
    return [segment for segment in path.split("/") if segment.startswith("scope_")]
