"""Tests for experimental content folder helpers and :class:`ContentFolder`."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.experimental.content_folder import functions as _functions
from unique_toolkit.experimental.content_folder.functions import (
    create_access,
    creator_scope_access_grants,
    read,
)
from unique_toolkit.experimental.content_folder.schemas import (
    AccessEntityType,
    AccessType,
    CreatedFolder,
    DeleteResult,
    FolderInfo,
    ScopeAccess,
)
from unique_toolkit.experimental.content_folder.service import ContentFolder

# ── Test fixtures ─────────────────────────────────────────────────────────────


_CREATED_ONE = {
    "createdFolders": [
        {"id": "scope_1", "object": "folder", "name": "n1", "parentId": None},
    ]
}
_FOLDER_DETAIL = {
    "id": "scope_1",
    "name": "n1",
    "scopeAccess": [],
    "children": [],
}
_FOLDER_INFO = {
    "id": "scope_1",
    "name": "n1",
    "ingestionConfig": {},
    "createdAt": None,
    "updatedAt": None,
    "parentId": None,
    "externalId": None,
}
_DELETE_RESULT = {"successFolders": [], "failedFolders": []}


def test_AI_create_raises_when_paths_and_parent_both_provided() -> None:
    """Reject mixing absolute ``paths=`` with ``parent_scope_id=`` / ``relative_path_segments=``."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    create = cast(Any, svc.create)
    with pytest.raises(TypeError, match="create:"):
        create(
            paths="/a",
            parent_scope_id="p",
            relative_path_segments=["x"],
        )


def test_AI_create_requires_paths_or_parent_shape() -> None:
    """``create`` must receive either ``paths=`` or parent+segments, not neither."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    create = cast(Any, svc.create)
    with pytest.raises(TypeError, match="create:"):
        create()


def test_AI_create_rejects_partial_parent_mode() -> None:
    """Parent mode requires BOTH ``parent_scope_id=`` and ``relative_path_segments=``.

    Supplying only one half must raise a service-level ``TypeError`` (matching the
    other shape errors on ``create``) rather than leaking as a downstream
    ``ValueError`` from the functions layer.
    """
    svc = ContentFolder(company_id="c1", user_id="u1")
    create = cast(Any, svc.create)

    with pytest.raises(TypeError, match="create:.*parent mode"):
        create(parent_scope_id="p")

    with pytest.raises(TypeError, match="create:.*parent mode"):
        create(relative_path_segments=["x"])


def test_AI_read_requires_exactly_one_address() -> None:
    """Low-level :func:`read` mirrors ``_build_get_params`` mutual-exclusion rules."""
    with pytest.raises(ValueError, match="exactly one"):
        read(user_id="u", company_id="c")

    with pytest.raises(ValueError, match="only one"):
        read(
            user_id="u",
            company_id="c",
            scope_id="s",
            folder_path="/x",
        )


def test_AI_create_access_validates_scope_address() -> None:
    """Access helpers must not send both ``scope_id`` and ``folder_path`` to the SDK."""
    with pytest.raises(ValueError, match="only one"):
        create_access(
            user_id="u",
            company_id="c",
            scope_id="s",
            folder_path="/x",
            scope_accesses=[],
        )


def test_AI_delete_result_parses_sdk_shape() -> None:
    """``DeleteResult`` wraps the SDK delete payload (success/failed folder rows)."""
    raw = {
        "successFolders": [{"id": "1", "name": "n", "path": "/p"}],
        "failedFolders": [],
    }
    result = DeleteResult.model_validate(raw, by_alias=True, by_name=True)
    assert len(result.success_folders) == 1
    assert result.success_folders[0].path == "/p"
    assert result.failed_folders == []


def test_AI_folder_info_preserves_ingestion_config_as_dict() -> None:
    """``FolderInfo.ingestion_config`` stays a plain dict until a typed model is introduced."""
    payload = {
        "id": "scope",
        "name": "nm",
        "ingestionConfig": {"uniqueIngestionMode": "MODE_A"},
        "createdAt": None,
        "updatedAt": None,
        "parentId": None,
        "externalId": None,
    }
    info = FolderInfo.model_validate(payload, by_alias=True, by_name=True)
    assert info.ingestion_config == {"uniqueIngestionMode": "MODE_A"}


@patch("unique_toolkit.experimental.content_folder.functions.create")
def test_AI_create_normalizes_single_path_string(mock_create: MagicMock) -> None:
    """A single ``paths=`` string is normalized to a one-element list for the SDK."""
    mock_create.return_value = []
    svc = ContentFolder(company_id="c", user_id="u")
    svc.create(paths="/a")
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["absolute_paths"] == ["/a"]


@patch("unique_toolkit.experimental.content_folder.functions.create_async")
@pytest.mark.asyncio
async def test_AI_create_async_has_same_overloads_as_create(
    mock_create_async: MagicMock,
) -> None:
    """Async ``create_async`` accepts the same ``paths=`` shapes as ``create``."""
    mock_create_async.return_value = []
    svc = ContentFolder(company_id="c", user_id="u")
    await svc.create_async(paths="/one")
    mock_create_async.assert_called_once()
    assert mock_create_async.call_args.kwargs["absolute_paths"] == ["/one"]


# ── functions.create / create_async ───────────────────────────────────────────


def test_AI_functions_create_calls_sdk_and_grants_creator_access() -> None:
    """``create`` forwards ``paths`` to the SDK and grants creator READ+WRITE by default."""
    with (
        patch("unique_sdk.Folder.create_paths") as mock_create,
        patch("unique_sdk.Folder.add_access") as mock_add,
    ):
        mock_create.return_value = _CREATED_ONE
        mock_add.return_value = _FOLDER_DETAIL

        result = _functions.create(
            user_id="u1",
            company_id="c1",
            absolute_paths=["/a"],
        )

    assert [f.id for f in result] == ["scope_1"]
    create_kwargs = mock_create.call_args.kwargs
    assert create_kwargs["user_id"] == "u1"
    assert create_kwargs["company_id"] == "c1"
    assert create_kwargs["paths"] == ["/a"]
    assert "inheritAccess" not in create_kwargs
    mock_add.assert_called_once()


def test_AI_functions_create_parent_mode_passes_parent_scope_id() -> None:
    """Parent mode sends ``parentScopeId`` + ``relativePaths`` to the SDK."""
    with (
        patch("unique_sdk.Folder.create_paths") as mock_create,
        patch("unique_sdk.Folder.add_access") as mock_add,
    ):
        mock_create.return_value = _CREATED_ONE
        mock_add.return_value = _FOLDER_DETAIL

        _functions.create(
            user_id="u",
            company_id="c",
            parent_scope_id="parent_1",
            relative_path_segments=["child"],
        )

    kwargs = mock_create.call_args.kwargs
    assert kwargs["parentScopeId"] == "parent_1"
    assert kwargs["relativePaths"] == ["child"]


def test_AI_functions_create_inherit_access_skips_creator_grant() -> None:
    """``inherit_access=True`` sets ``inheritAccess`` and skips the extra ``add_access`` call."""
    with (
        patch("unique_sdk.Folder.create_paths") as mock_create,
        patch("unique_sdk.Folder.add_access") as mock_add,
    ):
        mock_create.return_value = _CREATED_ONE

        _functions.create(
            user_id="u",
            company_id="c",
            absolute_paths=["/a"],
            inherit_access=True,
        )

    assert mock_create.call_args.kwargs.get("inheritAccess") is True
    mock_add.assert_not_called()


def test_AI_functions_create_private_false_skips_creator_grant() -> None:
    """``private_to_creator=False`` does not grant extra access on newly created folders."""
    with (
        patch("unique_sdk.Folder.create_paths") as mock_create,
        patch("unique_sdk.Folder.add_access") as mock_add,
    ):
        mock_create.return_value = _CREATED_ONE

        _functions.create(
            user_id="u",
            company_id="c",
            absolute_paths=["/a"],
            private_to_creator=False,
        )

    mock_add.assert_not_called()


@pytest.mark.asyncio
async def test_AI_functions_create_async_calls_sdk_and_grants_creator_access() -> None:
    """``create_async`` forwards ``paths`` and issues per-folder ``add_access`` concurrently."""
    with (
        patch(
            "unique_sdk.Folder.create_paths_async",
            new_callable=AsyncMock,
        ) as mock_create,
        patch(
            "unique_sdk.Folder.add_access_async",
            new_callable=AsyncMock,
        ) as mock_add,
    ):
        mock_create.return_value = _CREATED_ONE
        mock_add.return_value = _FOLDER_DETAIL

        result = await _functions.create_async(
            user_id="u",
            company_id="c",
            absolute_paths=["/a"],
        )

    assert [f.id for f in result] == ["scope_1"]
    mock_create.assert_awaited_once()
    mock_add.assert_awaited_once()


def test_AI_functions_create_requires_a_mode() -> None:
    """``_build_create_params`` rejects calls with neither absolute nor parent mode."""
    with pytest.raises(ValueError, match="Provide absolute_paths"):
        _functions.create(user_id="u", company_id="c")


def test_AI_functions_create_rejects_mixed_modes() -> None:
    """``_build_create_params`` rejects mixing ``absolute_paths`` with parent mode."""
    with pytest.raises(ValueError, match="Choose one creation style"):
        _functions.create(
            user_id="u",
            company_id="c",
            absolute_paths=["/a"],
            parent_scope_id="p",
            relative_path_segments=["x"],
        )


def test_AI_functions_create_rejects_empty_absolute_paths() -> None:
    """Empty ``absolute_paths`` must be refused, matching SDK expectations."""
    with pytest.raises(ValueError, match="absolute_paths must be a non-empty"):
        _functions.create(user_id="u", company_id="c", absolute_paths=[])


# ── creator_scope_access_grants ───────────────────────────────────────────────


def test_AI_creator_scope_access_grants_returns_read_and_write_for_user() -> None:
    """Creator defaults: two USER grants (READ + WRITE) for the acting user id."""
    grants = creator_scope_access_grants("u42")
    assert [(g.entity_id, g.type, g.entity_type) for g in grants] == [
        ("u42", AccessType.READ, AccessEntityType.USER),
        ("u42", AccessType.WRITE, AccessEntityType.USER),
    ]


# ── functions.read / read_async ───────────────────────────────────────────────


def test_AI_functions_read_sends_scope_id_to_sdk() -> None:
    """``read`` forwards ``scope_id`` as ``scopeId`` to ``Folder.get_info``."""
    with patch("unique_sdk.Folder.get_info") as mock_get:
        mock_get.return_value = _FOLDER_INFO

        info = _functions.read(user_id="u", company_id="c", scope_id="scope_1")

    assert info.id == "scope_1"
    assert mock_get.call_args.kwargs["scopeId"] == "scope_1"


def test_AI_functions_read_sends_folder_path_to_sdk() -> None:
    """``read`` forwards ``folder_path`` as ``folderPath`` to ``Folder.get_info``."""
    with patch("unique_sdk.Folder.get_info") as mock_get:
        mock_get.return_value = _FOLDER_INFO

        _functions.read(user_id="u", company_id="c", folder_path="/a")

    assert mock_get.call_args.kwargs["folderPath"] == "/a"


@pytest.mark.asyncio
async def test_AI_functions_read_async_forwards_to_sdk() -> None:
    """``read_async`` forwards to ``Folder.get_info_async`` with the right scope address."""
    with patch(
        "unique_sdk.Folder.get_info_async", new_callable=AsyncMock
    ) as mock_get_async:
        mock_get_async.return_value = _FOLDER_INFO

        info = await _functions.read_async(
            user_id="u", company_id="c", scope_id="scope_1"
        )

    assert info.id == "scope_1"
    mock_get_async.assert_awaited_once()


# ── functions.delete / delete_async ───────────────────────────────────────────


def test_AI_functions_delete_passes_scope_id_and_recursive() -> None:
    """``delete`` forwards ``scope_id`` + ``recursive`` flag to the SDK."""
    with patch("unique_sdk.Folder.delete") as mock_delete:
        mock_delete.return_value = _DELETE_RESULT

        result = _functions.delete(
            user_id="u",
            company_id="c",
            scope_id="scope_1",
            recursive=True,
        )

    assert isinstance(result, DeleteResult)
    kwargs = mock_delete.call_args.kwargs
    assert kwargs["scopeId"] == "scope_1"
    assert kwargs["recursive"] is True


def test_AI_functions_delete_by_folder_path_omits_recursive_by_default() -> None:
    """``delete`` with ``folder_path`` and default recursive=False sends ``folderPath`` only."""
    with patch("unique_sdk.Folder.delete") as mock_delete:
        mock_delete.return_value = _DELETE_RESULT

        _functions.delete(user_id="u", company_id="c", folder_path="/a")

    kwargs = mock_delete.call_args.kwargs
    assert kwargs["folderPath"] == "/a"
    assert "recursive" not in kwargs


@pytest.mark.asyncio
async def test_AI_functions_delete_async_forwards_to_sdk() -> None:
    """``delete_async`` forwards to ``Folder.delete_async``."""
    with patch(
        "unique_sdk.Folder.delete_async", new_callable=AsyncMock
    ) as mock_delete_async:
        mock_delete_async.return_value = _DELETE_RESULT

        result = await _functions.delete_async(
            user_id="u", company_id="c", scope_id="s"
        )

    assert isinstance(result, DeleteResult)
    mock_delete_async.assert_awaited_once()


# ── functions.create_access / delete_access (sync + async) ────────────────────


def _grant(entity_id: str) -> ScopeAccess:
    return ScopeAccess(
        entity_id=entity_id,
        type=AccessType.READ,
        entity_type=AccessEntityType.USER,
    )


def _leaf(scope_id: str = "leaf_scope", name: str = "leaf") -> CreatedFolder:
    return CreatedFolder(id=scope_id, object="folder", name=name)


def test_AI_functions_create_access_calls_sdk_add_access() -> None:
    """``create_access`` maps to ``Folder.add_access`` with camelCase params."""
    with patch("unique_sdk.Folder.add_access") as mock_add:
        mock_add.return_value = _FOLDER_DETAIL

        detail = _functions.create_access(
            user_id="u",
            company_id="c",
            scope_id="scope_1",
            scope_accesses=[_grant("u1")],
            apply_to_sub_scopes=True,
        )

    assert detail.id == "scope_1"
    kwargs = mock_add.call_args.kwargs
    assert kwargs["scopeId"] == "scope_1"
    assert kwargs["applyToSubScopes"] is True
    assert len(kwargs["scopeAccesses"]) == 1


@pytest.mark.asyncio
async def test_AI_functions_create_access_async_forwards_to_sdk() -> None:
    """``create_access_async`` maps to ``Folder.add_access_async``."""
    with patch(
        "unique_sdk.Folder.add_access_async", new_callable=AsyncMock
    ) as mock_add_async:
        mock_add_async.return_value = _FOLDER_DETAIL

        await _functions.create_access_async(
            user_id="u",
            company_id="c",
            folder_path="/a",
            scope_accesses=[_grant("u1")],
        )

    assert mock_add_async.await_args is not None
    assert mock_add_async.await_args.kwargs["folderPath"] == "/a"


def test_AI_functions_delete_access_calls_sdk_remove_access() -> None:
    """``delete_access`` maps to ``Folder.remove_access``."""
    with patch("unique_sdk.Folder.remove_access") as mock_remove:
        mock_remove.return_value = _FOLDER_DETAIL

        _functions.delete_access(
            user_id="u",
            company_id="c",
            scope_id="scope_1",
            scope_accesses=[_grant("u1")],
        )

    assert mock_remove.call_args.kwargs["scopeId"] == "scope_1"


@pytest.mark.asyncio
async def test_AI_functions_delete_access_async_forwards_to_sdk() -> None:
    """``delete_access_async`` maps to ``Folder.remove_access_async``."""
    with patch(
        "unique_sdk.Folder.remove_access_async", new_callable=AsyncMock
    ) as mock_remove_async:
        mock_remove_async.return_value = _FOLDER_DETAIL

        await _functions.delete_access_async(
            user_id="u",
            company_id="c",
            scope_id="scope_1",
            scope_accesses=[_grant("u1")],
        )

    mock_remove_async.assert_awaited_once()


# ── service delegation ────────────────────────────────────────────────────────


def test_AI_service_read_delegates_to_functions() -> None:
    """``ContentFolder.read`` calls the underlying :func:`read` with stored ids."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch(
        "unique_toolkit.experimental.content_folder.service._folder.read"
    ) as mock_read:
        mock_read.return_value = FolderInfo.model_validate(_FOLDER_INFO, by_alias=True)
        svc.read(scope_id="scope_1")

    kwargs = mock_read.call_args.kwargs
    assert kwargs["user_id"] == "u1"
    assert kwargs["company_id"] == "c1"
    assert kwargs["scope_id"] == "scope_1"


@pytest.mark.asyncio
async def test_AI_service_read_async_delegates_to_functions() -> None:
    """``ContentFolder.read_async`` forwards to the async functions layer."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch(
        "unique_toolkit.experimental.content_folder.service._folder.read_async",
        new_callable=AsyncMock,
    ) as mock_read_async:
        mock_read_async.return_value = FolderInfo.model_validate(
            _FOLDER_INFO, by_alias=True
        )
        await svc.read_async(folder_path="/a")

    assert mock_read_async.await_args is not None
    assert mock_read_async.await_args.kwargs["folder_path"] == "/a"


def test_AI_service_delete_delegates_to_functions() -> None:
    """``ContentFolder.delete`` forwards scope + recursive to the functions layer."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch(
        "unique_toolkit.experimental.content_folder.service._folder.delete"
    ) as mock_delete:
        mock_delete.return_value = DeleteResult.model_validate(
            _DELETE_RESULT, by_alias=True
        )
        svc.delete(scope_id="scope_1", recursive=True)

    kwargs = mock_delete.call_args.kwargs
    assert kwargs["scope_id"] == "scope_1"
    assert kwargs["recursive"] is True


@pytest.mark.asyncio
async def test_AI_service_delete_async_delegates_to_functions() -> None:
    """``ContentFolder.delete_async`` forwards to the async functions layer."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch(
        "unique_toolkit.experimental.content_folder.service._folder.delete_async",
        new_callable=AsyncMock,
    ) as mock_delete_async:
        mock_delete_async.return_value = DeleteResult.model_validate(
            _DELETE_RESULT, by_alias=True
        )
        await svc.delete_async(scope_id="scope_1")

    mock_delete_async.assert_awaited_once()


def test_AI_service_create_access_delegates_to_functions() -> None:
    """``ContentFolder.create_access`` forwards ``scope_accesses`` and scope address."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch(
        "unique_toolkit.experimental.content_folder.service._folder.create_access"
    ) as mock_ca:
        mock_ca.return_value = MagicMock()
        svc.create_access(scope_id="scope_1", scope_accesses=[_grant("u2")])

    assert mock_ca.call_args.kwargs["scope_id"] == "scope_1"


@pytest.mark.asyncio
async def test_AI_service_create_access_async_delegates_to_functions() -> None:
    """``ContentFolder.create_access_async`` forwards to the async functions layer."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch(
        "unique_toolkit.experimental.content_folder.service._folder.create_access_async",
        new_callable=AsyncMock,
    ) as mock_ca_async:
        mock_ca_async.return_value = MagicMock()
        await svc.create_access_async(
            folder_path="/a",
            scope_accesses=[_grant("u2")],
            apply_to_sub_scopes=True,
        )

    assert mock_ca_async.await_args is not None
    kwargs = mock_ca_async.await_args.kwargs
    assert kwargs["folder_path"] == "/a"
    assert kwargs["apply_to_sub_scopes"] is True


def test_AI_service_delete_access_delegates_to_functions() -> None:
    """``ContentFolder.delete_access`` forwards the scope address and grants."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch(
        "unique_toolkit.experimental.content_folder.service._folder.delete_access"
    ) as mock_da:
        mock_da.return_value = MagicMock()
        svc.delete_access(scope_id="scope_1", scope_accesses=[_grant("u2")])

    assert mock_da.call_args.kwargs["scope_id"] == "scope_1"


@pytest.mark.asyncio
async def test_AI_service_delete_access_async_delegates_to_functions() -> None:
    """``ContentFolder.delete_access_async`` forwards to the async functions layer."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch(
        "unique_toolkit.experimental.content_folder.service._folder.delete_access_async",
        new_callable=AsyncMock,
    ) as mock_da_async:
        mock_da_async.return_value = MagicMock()
        await svc.delete_access_async(scope_id="scope_1", scope_accesses=[_grant("u2")])

    mock_da_async.assert_awaited_once()


# ── create_with_access (sync + async) ─────────────────────────────────────────


def test_AI_service_create_with_access_calls_create_access_on_leaf() -> None:
    """``create_with_access`` creates folders, then grants extras on the leaf scope."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with (
        patch.object(svc, "_create_impl") as mock_create_impl,
        patch.object(svc, "create_access") as mock_create_access,
    ):
        mock_create_impl.return_value = [_leaf()]
        mock_create_access.return_value = MagicMock()

        created, _detail = svc.create_with_access(
            paths="/a",
            scope_accesses=[_grant("u2")],
            apply_to_sub_scopes=True,
        )

    assert created[0].id == "leaf_scope"
    kwargs = mock_create_access.call_args.kwargs
    assert kwargs["scope_id"] == "leaf_scope"
    assert kwargs["apply_to_sub_scopes"] is True


def test_AI_service_create_with_access_skips_add_access_when_empty() -> None:
    """With empty ``scope_accesses``, ``create_with_access`` returns a synthetic detail.

    The creator's READ+WRITE grants appear in the detail when ``private_to_creator``
    is on and ``inherit_access`` is off (which are the defaults).
    """
    svc = ContentFolder(company_id="c1", user_id="u1")
    with (
        patch.object(svc, "_create_impl") as mock_create_impl,
        patch.object(svc, "create_access") as mock_create_access,
    ):
        mock_create_impl.return_value = [_leaf()]

        _created, detail = svc.create_with_access(
            paths="/a",
            scope_accesses=[],
        )

    mock_create_access.assert_not_called()
    assert detail.id == "leaf_scope"
    assert len(detail.scope_access) == 2


def test_AI_service_create_with_access_raises_when_no_folder_created() -> None:
    """If the functions layer returns no folders, ``create_with_access`` surfaces a ``ValueError``."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch.object(svc, "_create_impl", return_value=[]):
        with pytest.raises(ValueError, match="No folder was returned"):
            svc.create_with_access(paths="/a", scope_accesses=[])


@pytest.mark.asyncio
async def test_AI_service_create_with_access_async_calls_create_access_async_on_leaf() -> (
    None
):
    """``create_with_access_async`` creates then grants on the leaf asynchronously."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with (
        patch.object(
            svc, "_create_impl_async", new_callable=AsyncMock
        ) as mock_create_impl_async,
        patch.object(
            svc, "create_access_async", new_callable=AsyncMock
        ) as mock_ca_async,
    ):
        mock_create_impl_async.return_value = [_leaf()]
        mock_ca_async.return_value = MagicMock()

        await svc.create_with_access_async(
            paths="/a",
            scope_accesses=[_grant("u2")],
        )

    mock_ca_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_AI_service_create_with_access_async_skips_when_empty() -> None:
    """Empty ``scope_accesses`` skips the async add-access call and returns a synthetic detail."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with (
        patch.object(
            svc, "_create_impl_async", new_callable=AsyncMock
        ) as mock_create_impl_async,
        patch.object(
            svc, "create_access_async", new_callable=AsyncMock
        ) as mock_ca_async,
    ):
        mock_create_impl_async.return_value = [_leaf()]

        _created, detail = await svc.create_with_access_async(
            paths="/a",
            scope_accesses=[],
        )

    mock_ca_async.assert_not_called()
    assert detail.id == "leaf_scope"


@pytest.mark.asyncio
async def test_AI_service_create_with_access_async_raises_when_empty_result() -> None:
    """If the async functions layer returns no folders, raise ``ValueError``."""
    svc = ContentFolder(company_id="c1", user_id="u1")
    with patch.object(
        svc, "_create_impl_async", new_callable=AsyncMock, return_value=[]
    ):
        with pytest.raises(ValueError, match="No folder was returned"):
            await svc.create_with_access_async(paths="/a", scope_accesses=[])
