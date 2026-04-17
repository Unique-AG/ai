from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, overload

import unique_sdk

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.content_folder.functions import (
    add_folder_access,
    add_folder_access_async,
    create_folders,
    create_folders_async,
    creator_scope_access_grants,
    get_folder_info,
    get_folder_info_async,
    remove_folder_access,
    remove_folder_access_async,
)
from unique_toolkit.experimental.content_folder.functions import (
    delete_folder as delete_folder_api,
)
from unique_toolkit.experimental.content_folder.functions import (
    delete_folder_async as delete_folder_async_api,
)
from unique_toolkit.experimental.content_folder.schemas import (
    CreatedFolder,
    FolderDetail,
    FolderInfo,
    ScopeAccess,
)

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueContext


class ContentFolder:
    """Manage knowledge-base folders and their READ/WRITE access.

    **Scope id:** A knowledge-base folder is a *content scope*; its id is ``scopeId`` in
    the HTTP API. The toolkit uses ``scope_id`` for that same string (e.g. the ``id`` field
    on :class:`~unique_toolkit.experimental.content_folder.schemas.CreatedFolder`).

    **Creating folders** — pick *one* style per call (type checkers enforce this via overloads):

    1. ``path=`` — a single absolute path from the knowledge-base root.
    2. ``paths=`` — several absolute paths at once.
    3. ``parent_scope_id=`` + ``relative_path_segments=`` — nested folders under an existing
       parent, using path **segments** (not a second full path). Maps to ``parentScopeId`` +
       ``relativePaths``.

    **Looking up or changing access** — pass either ``scope_id=`` *or* ``folder_path=``,
    never both.

    **Creator-private folders (default):** By default, new folders are not created with
    ``inherit_access``; after creation the toolkit grants the acting user READ and WRITE on
    each created scope (see ``private_to_creator``). That does not remove ACL rows the API
    may add for other principals—set ``private_to_creator=False`` only when you intend to
    rely on server defaults or will manage ACL yourself.

    **Delete:** Use :meth:`delete_folder` or :meth:`delete_folder_async` with either
    ``scope_id`` or ``folder_path`` (same addressing rules as :meth:`get_folder_info`).
    """

    def __init__(
        self,
        company_id: str,
        user_id: str,
    ) -> None:
        [company_id, user_id] = validate_required_values([company_id, user_id])
        self._company_id = company_id
        self._user_id = user_id

    # ── Construction ──────────────────────────────────────────────────────

    @classmethod
    def from_context(cls, context: UniqueContext) -> Self:
        """Create from a :class:`UniqueContext` (preferred constructor)."""
        return cls(
            company_id=context.auth.get_confidential_company_id(),
            user_id=context.auth.get_confidential_user_id(),
        )

    @classmethod
    def from_settings(
        cls,
        settings: UniqueSettings | str | None = None,
        **kwargs: Any,
    ) -> Self:
        """Create from :class:`UniqueSettings` (used by :class:`UniqueServiceFactory`)."""
        _ = kwargs

        if settings is None:
            settings = UniqueSettings.from_env_auto_with_sdk_init()
        elif isinstance(settings, str):
            settings = UniqueSettings.from_env_auto_with_sdk_init(filename=settings)

        return cls(
            company_id=settings.authcontext.get_confidential_company_id(),
            user_id=settings.authcontext.get_confidential_user_id(),
        )

    # ── Create ────────────────────────────────────────────────────────────

    @overload
    def create_folder(
        self,
        *,
        path: str,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    @overload
    def create_folder(
        self,
        *,
        paths: list[str],
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    @overload
    def create_folder(
        self,
        *,
        parent_scope_id: str,
        relative_path_segments: list[str],
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    def create_folder(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]:
        """Create folders. Use one overload shape only; mixing parameters raises ``TypeError``."""
        return self._create_folder_impl(
            path=path,
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

    async def create_folder_async(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]:
        """Async :meth:`create_folder` (same three call shapes: ``path=``, ``paths=``, or ``parent_scope_id=`` + ``relative_path_segments=``)."""
        return await self._create_folder_impl_async(
            path=path,
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

    def _create_folder_impl(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]:
        absolute, parent_id, segments = self._normalize_create_args(
            path=path,
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
        )
        return create_folders(
            user_id=self._user_id,
            company_id=self._company_id,
            absolute_paths=absolute,
            parent_scope_id=parent_id,
            relative_path_segments=segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

    async def _create_folder_impl_async(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]:
        absolute, parent_id, segments = self._normalize_create_args(
            path=path,
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
        )
        return await create_folders_async(
            user_id=self._user_id,
            company_id=self._company_id,
            absolute_paths=absolute,
            parent_scope_id=parent_id,
            relative_path_segments=segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

    def _normalize_create_args(
        self,
        *,
        path: str | None,
        paths: list[str] | None,
        parent_scope_id: str | None,
        relative_path_segments: list[str] | None,
    ) -> tuple[list[str] | None, str | None, list[str] | None]:
        """Return ``(absolute_paths, parent_scope_id, relative_path_segments)`` for the API layer."""
        n_path = 1 if path is not None else 0
        n_paths = 1 if paths is not None else 0
        n_under = (
            1
            if parent_scope_id is not None or relative_path_segments is not None
            else 0
        )

        if n_path + n_paths + n_under > 1:
            raise TypeError(
                "create_folder: use exactly one style — path=, paths=, or "
                "parent_scope_id= with relative_path_segments=."
            )

        if path is not None:
            return [path], None, None
        if paths is not None:
            return paths, None, None
        if parent_scope_id is not None or relative_path_segments is not None:
            return None, parent_scope_id, relative_path_segments

        raise TypeError(
            "create_folder: pass path=, paths=, or both parent_scope_id= and relative_path_segments=."
        )

    # ── Read ──────────────────────────────────────────────────────────────

    @overload
    def get_folder_info(self, *, scope_id: str) -> FolderInfo: ...

    @overload
    def get_folder_info(self, *, folder_path: str) -> FolderInfo: ...

    def get_folder_info(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> FolderInfo:
        """Load folder metadata by ``scope_id`` or ``folder_path`` (exactly one)."""
        return get_folder_info(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    async def get_folder_info_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> FolderInfo:
        """Async :meth:`get_folder_info` (pass exactly one of ``scope_id`` or ``folder_path``)."""
        return await get_folder_info_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    @overload
    def delete_folder(
        self,
        *,
        scope_id: str,
        recursive: bool = False,
    ) -> unique_sdk.Folder.DeleteResponse: ...

    @overload
    def delete_folder(
        self,
        *,
        folder_path: str,
        recursive: bool = False,
    ) -> unique_sdk.Folder.DeleteResponse: ...

    def delete_folder(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        recursive: bool = False,
    ) -> unique_sdk.Folder.DeleteResponse:
        """Delete a folder by ``scope_id`` or ``folder_path`` (exactly one)."""
        return delete_folder_api(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            recursive=recursive,
        )

    @overload
    async def delete_folder_async(
        self,
        *,
        scope_id: str,
        recursive: bool = False,
    ) -> unique_sdk.Folder.DeleteResponse: ...

    @overload
    async def delete_folder_async(
        self,
        *,
        folder_path: str,
        recursive: bool = False,
    ) -> unique_sdk.Folder.DeleteResponse: ...

    async def delete_folder_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        recursive: bool = False,
    ) -> unique_sdk.Folder.DeleteResponse:
        """Async :meth:`delete_folder` (exactly one of ``scope_id`` or ``folder_path``)."""
        return await delete_folder_async_api(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            recursive=recursive,
        )

    # ── Access management ─────────────────────────────────────────────────

    @overload
    def add_access(
        self,
        *,
        scope_id: str,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail: ...

    @overload
    def add_access(
        self,
        *,
        folder_path: str,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail: ...

    def add_access(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail:
        """Grant READ/WRITE on a folder (``scope_id=`` or ``folder_path=``)."""
        return add_folder_access(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
        )

    async def add_access_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail:
        """Async :meth:`add_access` (exactly one of ``scope_id`` or ``folder_path``)."""
        return await add_folder_access_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
        )

    @overload
    def remove_access(
        self,
        *,
        scope_id: str,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail: ...

    @overload
    def remove_access(
        self,
        *,
        folder_path: str,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail: ...

    def remove_access(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail:
        """Revoke access entries, addressed by id or path."""
        return remove_folder_access(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
        )

    async def remove_access_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail:
        """Async :meth:`remove_access` (exactly one of ``scope_id`` or ``folder_path``)."""
        return await remove_folder_access_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
        )

    # ── Create + access ───────────────────────────────────────────────────

    @overload
    def create_folder_with_access(
        self,
        *,
        path: str,
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    @overload
    def create_folder_with_access(
        self,
        *,
        paths: list[str],
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    @overload
    def create_folder_with_access(
        self,
        *,
        parent_scope_id: str,
        relative_path_segments: list[str],
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    def create_folder_with_access(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]:
        """Create folders, then grant ``scope_accesses`` on the leaf folder.

        Creator READ/WRITE on the created chain follows ``private_to_creator`` (same as
        :meth:`create_folder`). Extra principals/groups go in ``scope_accesses`` on the
        **last** folder in the create response (see :meth:`create_folder` for multi-path
        caveats).

        If ``scope_accesses`` is empty, no second ``add-access`` call is made; the returned
        :class:`~unique_toolkit.experimental.content_folder.schemas.FolderDetail` is a minimal view
        (leaf id/name and, when ``private_to_creator`` is true, the creator grants only).
        """
        created = self._create_folder_impl(
            path=path,
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

        leaf_scope_id = created[-1].id if created else None
        if leaf_scope_id is None:
            raise ValueError(
                "No folder was returned from create_folder; cannot attach access."
            )

        if scope_accesses:
            detail = self.add_access(
                scope_id=leaf_scope_id,
                scope_accesses=scope_accesses,
                apply_to_sub_scopes=apply_to_sub_scopes,
            )
        else:
            detail = FolderDetail(
                id=leaf_scope_id,
                name=created[-1].name,
                scope_access=(
                    creator_scope_access_grants(self._user_id)
                    if private_to_creator and not inherit_access
                    else []
                ),
                children=[],
            )
        return created, detail

    async def create_folder_with_access_async(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]:
        """Async :meth:`create_folder_with_access` (same create shapes as :meth:`create_folder_async`)."""
        created = await self._create_folder_impl_async(
            path=path,
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

        leaf_scope_id = created[-1].id if created else None
        if leaf_scope_id is None:
            raise ValueError(
                "No folder was returned from create_folder; cannot attach access."
            )

        if scope_accesses:
            detail = await self.add_access_async(
                scope_id=leaf_scope_id,
                scope_accesses=scope_accesses,
                apply_to_sub_scopes=apply_to_sub_scopes,
            )
        else:
            detail = FolderDetail(
                id=leaf_scope_id,
                name=created[-1].name,
                scope_access=(
                    creator_scope_access_grants(self._user_id)
                    if private_to_creator and not inherit_access
                    else []
                ),
                children=[],
            )
        return created, detail
