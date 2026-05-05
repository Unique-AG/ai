"""Shell state tracking the current working directory (path + scope_id)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import unique_sdk
from unique_sdk.cli.config import Config

_SEARCH_CONFIG_FILENAME = ".unique-search.json"


def _load_workspace_scope_ids() -> list[str]:
    config_path = Path.cwd() / _SEARCH_CONFIG_FILENAME
    if not config_path.is_file():
        return []
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return []
        scope_ids = data.get("scopeIds")
        if isinstance(scope_ids, list) and all(isinstance(s, str) for s in scope_ids):
            return scope_ids
    except (json.JSONDecodeError, OSError):
        pass
    return []


class ShellState:
    """Tracks the virtual working directory within the Unique folder hierarchy."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._path = "/"
        self._scope_id: str | None = None
        self.workspace_scope_ids: list[str] = _load_workspace_scope_ids()
        self._workspace_scope_paths: list[str] | None = None

    @property
    def workspace_restricted(self) -> bool:
        return bool(self.workspace_scope_ids)

    def _resolve_workspace_scope_paths(self) -> list[str]:
        """Lazily resolve workspace scope IDs to folder paths (one API call per scope, cached)."""
        if self._workspace_scope_paths is not None:
            return self._workspace_scope_paths
        paths: list[str] = []
        for scope_id in self.workspace_scope_ids:
            try:
                resp = unique_sdk.Folder.get_folder_path(
                    user_id=self.config.user_id,
                    company_id=self.config.company_id,
                    scope_id=scope_id,
                )
                p = resp.get("folderPath", "").rstrip("/")
                if p:  # empty after rstrip means the API returned "/" (root) — skip
                    paths.append(p)
            except Exception:
                pass
        self._workspace_scope_paths = paths
        return paths

    def is_within_workspace(self) -> bool:
        """Return True if the current path is inside (or is) a workspace scope root.

        Always returns True when no workspace restriction is configured.
        """
        if not self.workspace_scope_ids:
            return True
        if self._scope_id in self.workspace_scope_ids:
            return True
        paths = self._resolve_workspace_scope_paths()
        if not paths:
            return False
        current = self._path
        return any(current == p or current.startswith(p + "/") for p in paths)

    def is_folder_target_within_workspace(self, target: str) -> bool:
        """Check whether a folder target is within the workspace.

        For scope IDs and absolute paths the *target itself* is validated,
        not the current working directory.  Relative names fall back to the
        CWD check because they always resolve under the current directory.

        Always returns True when no workspace restriction is configured.
        """
        if not self.workspace_scope_ids:
            return True

        if target.startswith("scope_"):
            if target in self.workspace_scope_ids:
                return True
            paths = self._resolve_workspace_scope_paths()
            if not paths:
                return False
            try:
                resp = unique_sdk.Folder.get_folder_path(
                    user_id=self.config.user_id,
                    company_id=self.config.company_id,
                    scope_id=target,
                )
                p = resp.get("folderPath", "")
                return any(p == wp or p.startswith(wp + "/") for wp in paths)
            except Exception:
                return False

        if target.startswith("/"):
            # Normalize to collapse any `..` components before prefix-checking.
            # Without this, "/Workspace/../Evil" would pass a startswith("/Workspace/") check.
            normalized = os.path.normpath(target)
            paths = self._resolve_workspace_scope_paths()
            if not paths:
                return False
            return any(normalized == p or normalized.startswith(p + "/") for p in paths)

        # Relative path — resolve against CWD so that `../../outside` style
        # traversals are caught rather than delegating blindly to the CWD check.
        resolved = os.path.normpath(self._path.rstrip("/") + "/" + target)
        paths = self._resolve_workspace_scope_paths()
        if not paths:
            return self._scope_id in self.workspace_scope_ids
        return any(resolved == p or resolved.startswith(p + "/") for p in paths)

    @property
    def cwd(self) -> str:
        return self._path

    @property
    def scope_id(self) -> str | None:
        return self._scope_id

    @property
    def prompt(self) -> str:
        return f"{self._path}> "

    def cd(self, target: str) -> str:
        """Change directory. Returns the new path.

        Supports:
          - Absolute paths:  /Company/Reports
          - Relative names:  Reports
          - Parent:          ..
          - Root:            /
          - Scope IDs:       scope_abc123
        """
        if target == "/":
            self._path = "/"
            self._scope_id = None
            return self._path

        if target == "..":
            if self._path == "/":
                return self._path
            parts = self._path.rstrip("/").rsplit("/", 1)
            parent = parts[0] if parts[0] else "/"
            if parent == "/":
                self._path = "/"
                self._scope_id = None
            else:
                info = unique_sdk.Folder.get_info(
                    user_id=self.config.user_id,
                    company_id=self.config.company_id,
                    folderPath=parent,
                )
                self._path = parent
                self._scope_id = info["id"]
            return self._path

        if target.startswith("scope_"):
            info = unique_sdk.Folder.get_info(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                scopeId=target,
            )
            path_resp = unique_sdk.Folder.get_folder_path(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                scope_id=target,
            )
            self._scope_id = info["id"]
            self._path = path_resp["folderPath"]
            return self._path

        if target.startswith("/"):
            resolved_path = target
        else:
            resolved_path = f"{self._path.rstrip('/')}/{target}"

        info = unique_sdk.Folder.get_info(
            user_id=self.config.user_id,
            company_id=self.config.company_id,
            folderPath=resolved_path,
        )
        self._scope_id = info["id"]
        self._path = resolved_path
        return self._path

    def resolve_path(self, target: str | None) -> tuple[str, str | None]:
        """Resolve a target to (path, scope_id) without changing state.

        Returns the current directory if target is None.
        """
        if target is None:
            return self._path, self._scope_id

        if target == "/":
            return "/", None

        if target.startswith("scope_"):
            path_resp = unique_sdk.Folder.get_folder_path(
                user_id=self.config.user_id,
                company_id=self.config.company_id,
                scope_id=target,
            )
            return path_resp["folderPath"], target

        if target.startswith("/"):
            resolved_path = target
        else:
            resolved_path = f"{self._path.rstrip('/')}/{target}"

        info = unique_sdk.Folder.get_info(
            user_id=self.config.user_id,
            company_id=self.config.company_id,
            folderPath=resolved_path,
        )
        return resolved_path, info["id"]
