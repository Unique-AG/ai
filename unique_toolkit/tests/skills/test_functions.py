from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.skills import get_readable_skill_versions_async


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_readable_skill_versions_async__maps_content_id_to_updated_at() -> (
    None
):
    """
    Purpose: Verify the platform's skill list becomes a content-ID to last-modified map.
    Why this matters: Callers key a cache on these two values and skip anything not listed.
    Setup summary: Mock Space.get_skills_async with stamped and unstamped skills, assert the map.
    """
    # Arrange
    response = {
        "spaceId": "assistant_1",
        "skills": [
            {
                "contentId": "cont_a",
                "scopeId": "scope_a",
                "name": "pdf",
                "updatedAt": "2026-11-20T10:00:00.000Z",
            },
            {
                "contentId": "cont_b",
                "scopeId": "scope_b",
                "name": "docx",
                "updatedAt": None,
            },
        ],
    }

    with patch(
        "unique_toolkit.skills.functions.unique_sdk.Space.get_skills_async",
        new=AsyncMock(return_value=response),
    ) as mock_get_skills:
        # Act
        versions = await get_readable_skill_versions_async(
            user_id="user_1", company_id="company_1", space_id="assistant_1"
        )

    # Assert
    assert versions == {"cont_a": "2026-11-20T10:00:00.000Z"}
    mock_get_skills.assert_awaited_once_with(
        user_id="user_1", company_id="company_1", space_id="assistant_1"
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_readable_skill_versions_async__returns_empty_map__when_no_skills() -> (
    None
):
    """
    Purpose: Verify an empty platform list yields an empty map.
    Why this matters: A space without readable skills must not be treated as an error.
    Setup summary: Mock Space.get_skills_async with no skills, assert an empty dict.
    """
    with patch(
        "unique_toolkit.skills.functions.unique_sdk.Space.get_skills_async",
        new=AsyncMock(return_value={"spaceId": "assistant_1", "skills": []}),
    ):
        versions = await get_readable_skill_versions_async(
            user_id="user_1", company_id="company_1", space_id="assistant_1"
        )

    assert versions == {}
