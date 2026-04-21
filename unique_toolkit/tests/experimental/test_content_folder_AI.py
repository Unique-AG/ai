"""Tests for experimental content folder helpers and :class:`ContentFolder`."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit.experimental.content_folder.functions import (
    create_access,
    read,
)
from unique_toolkit.experimental.content_folder.schemas import DeleteResult, FolderInfo
from unique_toolkit.experimental.content_folder.service import ContentFolder


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
