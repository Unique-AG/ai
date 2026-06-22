from unittest.mock import AsyncMock, patch

import pytest

import unique_sdk
from unique_sdk.api_resources._folder import Folder

USER_ID = "user_test123"
COMPANY_ID = "company_test456"
FOLDER_ID = "scope_source123"
PARENT_ID = "scope_parent456"


@pytest.fixture
def move_result() -> Folder.MoveResult:
    return {
        "scopeId": FOLDER_ID,
        "asyncMetadataRebuild": False,
        "affectedFiles": 0,
        "message": None,
        "object": "folder-move",
    }


@pytest.mark.ai
def test_folder_move__sends_post_request_to_scoped_move_endpoint(
    move_result: Folder.MoveResult,
) -> None:
    with patch.object(Folder, "_static_request", return_value=move_result) as mock_req:
        result = unique_sdk.Folder.move(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            folderId=FOLDER_ID,
            newParentId=PARENT_ID,
        )

    mock_req.assert_called_once_with(
        "post",
        f"/folder/{FOLDER_ID}/move",
        USER_ID,
        company_id=COMPANY_ID,
        params={"newParentId": PARENT_ID},
    )
    assert result["scopeId"] == FOLDER_ID
    assert result["object"] == "folder-move"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_folder_move_async__sends_post_request_to_scoped_move_endpoint(
    move_result: Folder.MoveResult,
) -> None:
    with patch.object(
        Folder,
        "_static_request_async",
        new=AsyncMock(return_value=move_result),
    ) as mock_req:
        result = await unique_sdk.Folder.move_async(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            folderId=FOLDER_ID,
            newParentId=PARENT_ID,
        )

    mock_req.assert_awaited_once_with(
        "post",
        f"/folder/{FOLDER_ID}/move",
        USER_ID,
        company_id=COMPANY_ID,
        params={"newParentId": PARENT_ID},
    )
    assert result["scopeId"] == FOLDER_ID
