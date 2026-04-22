from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, overload

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.content_folder import functions as _folder
from unique_toolkit.experimental.content_folder.schemas import (
    CreatedFolder,
    DeleteResult,
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

    1. ``paths=`` — one or more absolute paths from the knowledge-base root (``str`` is
       treated as a single path).
    2. ``parent_scope_id=`` + ``relative_path_segments=`` — nested folders under an existing
       parent, using path **segments** (not a second full path). Maps to ``parentScopeId`` +
       ``relativePaths``.

    **Looking up or changing access** — pass either ``scope_id=`` *or* ``folder_path=``,
    never both.

    **Creator-private folders (default):** By default, new folders are not created with
    ``inherit_access``; after creation the toolkit grants the acting user READ and WRITE on
    each created scope (see ``private_to_creator``). That does not remove ACL rows the API
    may add for other principals—set ``private_to_creator=False`` only when you intend to
    rely on server defaults or will manage ACL yourself.

    **Delete:** Use :meth:`delete` or :meth:`delete_async` with either
    ``scope_id`` or ``folder_path`` (same addressing rules as :meth:`read`).
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
    def create(
        self,
        *,
        paths: str,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    @overload
    def create(
        self,
        *,
        paths: list[str],
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    @overload
    def create(
        self,
        *,
        parent_scope_id: str,
        relative_path_segments: list[str],
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    def create(
        self,
        *,
        paths: str | list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]:
        """Create folders. Use one overload shape only; mixing parameters raises ``TypeError``."""
        return self._create_impl(
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

    @overload
    async def create_async(
        self,
        *,
        paths: str,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    @overload
    async def create_async(
        self,
        *,
        paths: list[str],
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    @overload
    async def create_async(
        self,
        *,
        parent_scope_id: str,
        relative_path_segments: list[str],
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]: ...

    async def create_async(
        self,
        *,
        paths: str | list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]:
        """Async :meth:`create` (same shapes: ``paths=``, or ``parent_scope_id=`` + ``relative_path_segments=``)."""
        return await self._create_impl_async(
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

    def _create_impl(
        self,
        *,
        paths: str | list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]:
        absolute, parent_id, segments = self._normalize_create_args(
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
        )
        return _folder.create(
            user_id=self._user_id,
            company_id=self._company_id,
            absolute_paths=absolute,
            parent_scope_id=parent_id,
            relative_path_segments=segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

    async def _create_impl_async(
        self,
        *,
        paths: str | list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        inherit_access: bool = False,
        private_to_creator: bool = True,
    ) -> list[CreatedFolder]:
        absolute, parent_id, segments = self._normalize_create_args(
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
        )
        return await _folder.create_async(
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
        paths: str | list[str] | None,
        parent_scope_id: str | None,
        relative_path_segments: list[str] | None,
    ) -> tuple[list[str] | None, str | None, list[str] | None]:
        """Return ``(absolute_paths, parent_scope_id, relative_path_segments)`` for the API layer."""
        has_paths = paths is not None
        has_parent_any = (
            parent_scope_id is not None or relative_path_segments is not None
        )
        has_parent_full = (
            parent_scope_id is not None and relative_path_segments is not None
        )

        if has_paths and has_parent_any:
            raise TypeError(
                "create: use exactly one style — paths=, or "
                "parent_scope_id= with relative_path_segments=."
            )

        if has_paths:
            assert paths is not None
            absolute = [paths] if isinstance(paths, str) else paths
            return absolute, None, None

        if has_parent_any and not has_parent_full:
            raise TypeError(
                "create: parent mode requires both parent_scope_id= and "
                "relative_path_segments=."
            )

        if has_parent_full:
            return None, parent_scope_id, relative_path_segments

        raise TypeError(
            "create: pass paths=, or both parent_scope_id= and relative_path_segments=."
        )

    # ── Read ──────────────────────────────────────────────────────────────

    @overload
    def read(self, *, scope_id: str) -> FolderInfo: ...

    @overload
    def read(self, *, folder_path: str) -> FolderInfo: ...

    def read(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> FolderInfo:
        """Load folder metadata by ``scope_id`` or ``folder_path`` (exactly one)."""
        return _folder.read(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    async def read_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> FolderInfo:
        """Async :meth:`read` (pass exactly one of ``scope_id`` or ``folder_path``)."""
        return await _folder.read_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    @overload
    def delete(
        self,
        *,
        scope_id: str,
        recursive: bool = False,
    ) -> DeleteResult: ...

    @overload
    def delete(
        self,
        *,
        folder_path: str,
        recursive: bool = False,
    ) -> DeleteResult: ...

    def delete(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        recursive: bool = False,
    ) -> DeleteResult:
        """Delete a folder by ``scope_id`` or ``folder_path`` (exactly one)."""
        return _folder.delete(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            recursive=recursive,
        )

    @overload
    async def delete_async(
        self,
        *,
        scope_id: str,
        recursive: bool = False,
    ) -> DeleteResult: ...

    @overload
    async def delete_async(
        self,
        *,
        folder_path: str,
        recursive: bool = False,
    ) -> DeleteResult: ...

    async def delete_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        recursive: bool = False,
    ) -> DeleteResult:
        """Async :meth:`delete` (exactly one of ``scope_id`` or ``folder_path``)."""
        return await _folder.delete_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            recursive=recursive,
        )

    # ── Access management ─────────────────────────────────────────────────

    @overload
    def create_access(
        self,
        *,
        scope_id: str,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail: ...

    @overload
    def create_access(
        self,
        *,
        folder_path: str,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail: ...

    def create_access(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail:
        """Grant READ/WRITE on a folder (``scope_id=`` or ``folder_path=``)."""
        return _folder.create_access(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
        )

    async def create_access_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail:
        """Async :meth:`create_access` (exactly one of ``scope_id`` or ``folder_path``)."""
        return await _folder.create_access_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
        )

    @overload
    def delete_access(
        self,
        *,
        scope_id: str,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail: ...

    @overload
    def delete_access(
        self,
        *,
        folder_path: str,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail: ...

    def delete_access(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail:
        """Revoke access entries, addressed by id or path."""
        return _folder.delete_access(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
        )

    async def delete_access_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        scope_accesses: list[ScopeAccess],
        apply_to_sub_scopes: bool = False,
    ) -> FolderDetail:
        """Async :meth:`delete_access` (exactly one of ``scope_id`` or ``folder_path``)."""
        return await _folder.delete_access_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
        )

    # ── Create + access ───────────────────────────────────────────────────

    @overload
    def create_with_access(
        self,
        *,
        paths: str,
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    @overload
    def create_with_access(
        self,
        *,
        paths: list[str],
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    @overload
    def create_with_access(
        self,
        *,
        parent_scope_id: str,
        relative_path_segments: list[str],
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    def create_with_access(
        self,
        *,
        paths: str | list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]:
        """Create folders, then grant ``scope_accesses`` on the leaf folder.

        Creator READ/WRITE on the created chain follows ``private_to_creator`` (same as
        :meth:`create`). Extra principals/groups go in ``scope_accesses`` on the
        **last** folder in the create response (see :meth:`create` for multi-path
        caveats).

        If ``scope_accesses`` is empty, no second ``add-access`` call is made; the returned
        :class:`~unique_toolkit.experimental.content_folder.schemas.FolderDetail` is a minimal view
        (leaf id/name and, when ``private_to_creator`` is true, the creator grants only).
        """
        created = self._create_impl(
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

        leaf_scope_id = created[-1].id if created else None
        if leaf_scope_id is None:
            raise ValueError(
                "No folder was returned from create; cannot attach access."
            )

        if scope_accesses:
            detail = self.create_access(
                scope_id=leaf_scope_id,
                scope_accesses=scope_accesses,
                apply_to_sub_scopes=apply_to_sub_scopes,
            )
        else:
            detail = FolderDetail(
                id=leaf_scope_id,
                name=created[-1].name,
                scope_access=(
                    _folder.creator_scope_access_grants(self._user_id)
                    if private_to_creator and not inherit_access
                    else []
                ),
                children=[],
            )
        return created, detail

    @overload
    async def create_with_access_async(
        self,
        *,
        paths: str,
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    @overload
    async def create_with_access_async(
        self,
        *,
        paths: list[str],
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    @overload
    async def create_with_access_async(
        self,
        *,
        parent_scope_id: str,
        relative_path_segments: list[str],
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]: ...

    async def create_with_access_async(
        self,
        *,
        paths: str | list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_path_segments: list[str] | None = None,
        scope_accesses: list[ScopeAccess],
        inherit_access: bool = False,
        private_to_creator: bool = True,
        apply_to_sub_scopes: bool = False,
    ) -> tuple[list[CreatedFolder], FolderDetail]:
        """Async :meth:`create_with_access` (same create shapes as :meth:`create_async`)."""
        created = await self._create_impl_async(
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_path_segments=relative_path_segments,
            inherit_access=inherit_access,
            private_to_creator=private_to_creator,
        )

        leaf_scope_id = created[-1].id if created else None
        if leaf_scope_id is None:
            raise ValueError(
                "No folder was returned from create; cannot attach access."
            )

        if scope_accesses:
            detail = await self.create_access_async(
                scope_id=leaf_scope_id,
                scope_accesses=scope_accesses,
                apply_to_sub_scopes=apply_to_sub_scopes,
            )
        else:
            detail = FolderDetail(
                id=leaf_scope_id,
                name=created[-1].name,
                scope_access=(
                    _folder.creator_scope_access_grants(self._user_id)
                    if private_to_creator and not inherit_access
                    else []
                ),
                children=[],
            )
        return created, detail
