"""Unit tests for ``Folder`` response TypedDict shapes (folder public API parity)."""

from __future__ import annotations

import unique_sdk


def test_AI_folder_info_includes_scope_access_and_object_tags():
    """Folder info lists mirror API payloads with scopeAccess and optional object."""
    row: unique_sdk.Folder.FolderInfo = {
        "id": "scope_1",
        "name": "Docs",
        "ingestionConfig": {"uniqueIngestionMode": "INGESTION"},
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-01-02T00:00:00Z",
        "parentId": "scope_root",
        "externalId": "ext_1",
        "scopeAccess": [
            {
                "entityId": "user_1",
                "type": "READ",
                "entityType": "USER",
                "object": "scopeAccess",
            }
        ],
        "object": "folder-info",
    }
    assert row["scopeAccess"][0]["entityId"] == "user_1"


def test_AI_folder_infos_and_delete_and_path_responses_allow_object_tag():
    """Paginated folder list, delete batch, and path responses expose optional object."""
    infos: unique_sdk.Folder.FolderInfos = {
        "folderInfos": [],
        "totalCount": 0,
        "object": "folder-infos",
    }
    deleted: unique_sdk.Folder.DeleteResponse = {
        "successFolders": [],
        "failedFolders": [],
        "object": "deleted-folders",
    }
    path: unique_sdk.Folder.FolderPathResponse = {
        "folderPath": "/a/b",
        "object": "folder-path",
    }
    assert infos["object"] == "folder-infos"
    assert deleted["object"] == "deleted-folders"
    assert path["object"] == "folder-path"


def test_AI_ingestion_config_accepts_hide_in_chat():
    """Ingestion config matches optional hideInChat from the shared ingestion DTO."""
    cfg: unique_sdk.Folder.IngestionConfig = {
        "uniqueIngestionMode": "INGESTION",
        "hideInChat": True,
    }
    assert cfg["hideInChat"] is True
