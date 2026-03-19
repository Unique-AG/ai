"""Shell state tracking the current working directory (path + scope_id)."""

from __future__ import annotations

import unique_sdk

from unique_sdk.cli.config import Config


class ShellState:
    """Tracks the virtual working directory within the Unique folder hierarchy."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._path = "/"
        self._scope_id: str | None = None

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
