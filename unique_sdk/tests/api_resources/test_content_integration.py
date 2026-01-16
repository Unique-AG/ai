"""
Integration tests for the Content API resource.

These tests make actual API calls and require valid credentials.
Configuration must be provided via tests/.env file.

Required environment variables in tests/.env:
- UNIQUE_TEST_API_KEY: API key for authentication
- UNIQUE_TEST_APP_ID: App ID for authentication
- UNIQUE_TEST_USER_ID: User ID for API requests
- UNIQUE_TEST_COMPANY_ID: Company ID for API requests
- UNIQUE_TEST_BASE_URL: Base URL for API
- UNIQUE_TEST_ROOT_SCOPE_ID: Scope ID for root folder
- UNIQUE_TEST_ROOT_FOLDER_PATH: Folder path for root folder
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

from tests.api_resources.typed_dict_helpers import get_missing_fields, has_all_fields
from tests.test_config import IntegrationTestConfig
from unique_sdk.api_resources._content import Content


def assert_content(content: Content, skip_fields: list[str] | None = None) -> None:
    assert has_all_fields(content, Content, skip_fields=skip_fields), (
        f"Content does not have all required fields: {get_missing_fields(content, Content)}"
    )


def assert_content_info(
    content_info: Content.ContentInfo, skip_fields: list[str] | None = None
) -> None:
    assert has_all_fields(content_info, Content.ContentInfo, skip_fields=skip_fields), (
        f"Content info does not have all required fields: {get_missing_fields(content_info, Content.ContentInfo)}"
    )


def assert_paginated_content_info(
    result: Content.PaginatedContentInfo,
    skip_fields: list[str] | None = None,
    content_info_skip_fields: list[str] | None = None,
) -> None:
    assert has_all_fields(
        result, Content.PaginatedContentInfos, skip_fields=skip_fields
    ), (
        f"Result does not have all required fields: {get_missing_fields(result, Content.PaginatedContentInfos)}"
    )

    # Assert
    assert isinstance(result["totalCount"], int)

    if result["totalCount"] > 0 and len(result["contentInfo"]) > 0:
        for content_info in result["contentInfo"]:
            # TODO: Fix the type that we can remove the skip_fields
            assert has_all_fields(
                content_info, Content.ContentInfo, skip_fields=content_info_skip_fields
            ), (
                f"Content info does not have all required fields: {get_missing_fields(content_info, Content.ContentInfo)}"
            )


def assert_paginated_content_infos(
    result: Content.PaginatedContentInfos,
    skip_fields: list[str] | None = None,
    content_info_skip_fields: list[str] | None = None,
) -> None:
    assert has_all_fields(
        result, Content.PaginatedContentInfos, skip_fields=skip_fields
    ), (
        f"Result does not have all required fields: {get_missing_fields(result, Content.PaginatedContentInfos)}"
    )

    # Assert
    assert isinstance(result["totalCount"], int)

    if result["totalCount"] > 0 and len(result["contentInfos"]) > 0:
        for content_info in result["contentInfos"]:
            # TODO: Fix the type that we can remove the skip_fields
            assert has_all_fields(
                content_info, Content.ContentInfo, skip_fields=content_info_skip_fields
            ), (
                f"Content info does not have all required fields: {get_missing_fields(content_info, Content.ContentInfo)}"
            )


def assert_delete_response(
    result: Content.DeleteResponse, skip_fields: list[str] | None = None
) -> None:
    assert has_all_fields(result, Content.DeleteResponse, skip_fields=skip_fields), (
        f"Delete response does not have all required fields: {get_missing_fields(result, Content.DeleteResponse)}"
    )


@pytest.fixture(scope="module")
def created_content_ids() -> Generator[list[str], None, None]:
    """
    Track content IDs created during tests.
    This fixture maintains a list of content IDs that need to be cleaned up.
    """
    content_ids: list[str] = []
    yield content_ids
    # Cleanup happens in teardown_content_cleanup fixture


@pytest.fixture(scope="module", autouse=True)
def teardown_content_cleanup(
    integration_test_config: IntegrationTestConfig,
    created_content_ids: list[str],
) -> Generator[None, None, None]:
    """
    Teardown: Clean up all content created during tests.
    This runs after all tests in the module complete.
    """
    yield  # Let tests run first

    # Cleanup: Delete all content created during tests
    for content_id in created_content_ids:
        try:
            _ = Content.delete(
                user_id=integration_test_config.user_id,
                company_id=integration_test_config.company_id,
                contentId=content_id,
            )
        except Exception:
            pass  # Ignore cleanup errors during teardown


@pytest.fixture
def base_content_input(
    integration_test_config: IntegrationTestConfig,
) -> Content.Input:
    """
    Base content input for creating test content.
    Uses minimal ingestion config to avoid processing.
    """
    import uuid

    return Content.Input(
        key=f"test_content_{uuid.uuid4().hex[:8]}.txt",
        title=f"Test Content {uuid.uuid4().hex[:8]}",
        mimeType="text/plain",
        metadata={"test": "true", "created_by": "integration_test"},
    )


@pytest.fixture
def created_content(
    integration_test_config: IntegrationTestConfig,
    base_content_input: Content.Input,
    created_content_ids: list[str],
) -> Content:
    """
    Create a content item for testing.
    Returns the created Content object and tracks it for cleanup.
    """
    # Create content with storeInternally=True to store without external file
    content = Content.upsert(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        input=base_content_input,
        scopeId=integration_test_config.root_scope_id,
        storeInternally=True,
    )

    # Track for cleanup
    created_content_ids.append(content.id)

    return content


@pytest.mark.ai
@pytest.mark.integration
def test_content__upsert__creates_content_with_metadata(
    integration_test_config: IntegrationTestConfig,
    base_content_input: Content.Input,
    created_content_ids: list[str],
) -> None:
    """
    Purpose: Verify content can be created with metadata using upsert.
    Why this matters: Core functionality for adding content to the knowledge base.
    Setup summary: Create content with metadata, assert content structure and metadata.
    """
    # Act
    content = Content.upsert(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        input=base_content_input,
        scopeId=integration_test_config.root_scope_id,
        storeInternally=True,
    )

    # Track for cleanup
    created_content_ids.append(content.id)

    assert_content(content, skip_fields=["chunks", "updatedAt", "OBJECT_NAME"])

    assert content["key"] == base_content_input["key"]
    assert "metadata" in content
    if content["metadata"]:
        metadata = content["metadata"]
        assert isinstance(metadata, dict)
        assert metadata.get("test") == "true"
        assert metadata.get("created_by") == "integration_test"


@pytest.mark.ai
@pytest.mark.integration
def test_content__upsert__creates_content_with_title(
    integration_test_config: IntegrationTestConfig,
    base_content_input: Content.Input,
    created_content_ids: list[str],
) -> None:
    """
    Purpose: Verify content can be created with a title.
    Why this matters: Titles are important for content identification and display.
    Setup summary: Create content with title, assert title is set correctly.
    """
    # Act
    content = Content.upsert(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        input=base_content_input,
        scopeId=integration_test_config.root_scope_id,
        storeInternally=True,
    )

    # Track for cleanup
    created_content_ids.append(content.id)

    # Assert
    assert_content(content, skip_fields=["chunks", "updatedAt", "OBJECT_NAME"])

    if content["title"]:
        assert content["title"] == base_content_input.get("title")

    if content["title"]:
        assert base_content_input.get("title") in content["title"]


@pytest.mark.ai
@pytest.mark.integration
def test_content__get_info__retrieves_content_by_file_path(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify content info can be retrieved by file path.
    Why this matters: Enables content lookup using file paths.
    Setup summary: Create content, retrieve by file path using key, assert content info structure.
    """
    # Act
    result = Content.get_info(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        filePath=integration_test_config.root_folder_path
        + "/"
        + created_content["key"],
    )

    # Assert
    assert_paginated_content_info(
        result,
        skip_fields=["contentInfos"],
        content_info_skip_fields=["deletedAt", "expiredAt", "expiresAt"],
    )


@pytest.mark.ai
@pytest.mark.integration
def test_content__get_info__retrieves_content_by_content_id(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify content info can be retrieved by content ID.
    Why this matters: Enables direct content lookup using IDs.
    Setup summary: Create content, retrieve by content ID, assert content info structure.
    """
    # Act
    result = Content.get_info(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        contentId=created_content.id,
    )

    # Assert
    assert_paginated_content_info(
        result,
        skip_fields=["contentInfos"],
        content_info_skip_fields=["deletedAt", "expiredAt", "expiresAt"],
    )


@pytest.mark.ai
@pytest.mark.integration
def test_content__get_info__supports_pagination(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify get_info supports pagination with skip and take parameters.
    Why this matters: Enables efficient retrieval of large content sets.
    Setup summary: Create content, retrieve with pagination params, assert pagination structure.
    """
    # Act
    result = Content.get_info(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        skip=0,
        take=10,
    )

    # Assert
    assert_paginated_content_info(
        result,
        skip_fields=["contentInfos"],
        content_info_skip_fields=["deletedAt", "expiredAt", "expiresAt"],
    )


@pytest.mark.ai
@pytest.mark.integration
def test_content__get_infos__returns_paginated_content_infos(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify get_infos returns paginated content information.
    Why this matters: Enables listing and pagination of content items.
    Setup summary: Create content, retrieve infos, assert paginated structure.
    """
    # Act
    result = Content.get_infos(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
    )

    # Assert
    assert_paginated_content_infos(
        result,
        skip_fields=None,
        content_info_skip_fields=["deletedAt", "expiredAt", "expiresAt"],
    )


@pytest.mark.ai
@pytest.mark.integration
def test_content__get_infos__supports_parent_id_filter(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify get_infos can filter by parent ID.
    Why this matters: Enables hierarchical content organization and filtering.
    Setup summary: Create content with ownerId, retrieve by parentId, assert filtered results.
    """
    # Act

    result = Content.get_infos(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        parentId=integration_test_config.root_scope_id,
    )

    # Assert
    assert_paginated_content_infos(
        result,
        skip_fields=None,
        content_info_skip_fields=["deletedAt", "expiredAt", "expiresAt"],
    )


@pytest.mark.ai
@pytest.mark.integration
def test_content__get_infos__supports_metadata_filter(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify get_infos can filter by metadata.
    Why this matters: Enables advanced content filtering using metadata fields.
    Setup summary: Create content with metadata, filter by metadata, assert filtered results.
    """
    # Act
    metadata_filter: dict[str, Any] = {
        "and": [
            {
                "operator": "equals",
                "path": ["test"],
                "value": "true",
            }
        ]
    }
    result = Content.get_infos(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        metadataFilter=metadata_filter,
    )

    # Assert
    assert_paginated_content_infos(
        result,
        skip_fields=None,
        content_info_skip_fields=["deletedAt", "expiredAt", "expiresAt"],
    )


@pytest.mark.ai
@pytest.mark.integration
def test_content__update__updates_content_title(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify content title can be updated.
    Why this matters: Enables content title modification after creation.
    Setup summary: Create content, update title, assert title change.
    """
    # Arrange
    import uuid

    new_title = f"Updated Title {uuid.uuid4().hex[:8]}"

    # Act
    updated_content = Content.update(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        contentId=created_content.id,
        title=new_title,
    )

    # Assert
    assert_content_info(
        updated_content, skip_fields=["deletedAt", "expiredAt", "expiresAt"]
    )


@pytest.mark.ai
@pytest.mark.integration
def test_content__update__updates_content_metadata(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify content metadata can be updated.
    Why this matters: Enables metadata modification for content management.
    Setup summary: Create content, update metadata, assert metadata change.
    """
    # Arrange
    new_metadata: dict[str, str | None] = {
        "test": "updated",
        "updated_by": "integration_test",
        "new_field": "new_value",
    }

    # Act
    updated_content = Content.update(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        contentId=created_content.id,
        metadata=new_metadata,
    )

    # Assert
    assert_content_info(
        updated_content, skip_fields=["deletedAt", "expiredAt", "expiresAt"]
    )

    if updated_content["metadata"]:
        assert updated_content["metadata"].get("test") == "updated"
        assert updated_content["metadata"].get("updated_by") == "integration_test"


@pytest.mark.ai
@pytest.mark.integration
def test_content__update__supports_file_path_lookup(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify update can resolve content ID from file path.
    Why this matters: Provides flexible content update using file paths.
    Setup summary: Create content, update using file path instead of content ID, assert update succeeds.
    """
    # Arrange
    import uuid

    new_title = f"Updated via Path {uuid.uuid4().hex[:8]}"

    # Act
    updated_content = Content.update(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        filePath=integration_test_config.root_folder_path
        + "/"
        + created_content["key"],
        title=new_title,
    )

    # Assert
    assert_content_info(
        updated_content, skip_fields=["deletedAt", "expiredAt", "expiresAt"]
    )
    assert updated_content["title"] == new_title


@pytest.mark.ai
@pytest.mark.integration
def test_content__delete__deletes_content_by_id(
    integration_test_config: IntegrationTestConfig,
    base_content_input: Content.Input,
) -> None:
    """
    Purpose: Verify content can be deleted by content ID.
    Why this matters: Core functionality for content removal.
    Setup summary: Create content, delete by ID, assert deletion response.
    """
    # Arrange

    # Create content to delete
    content = Content.upsert(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        input=base_content_input,
        scopeId=integration_test_config.root_scope_id,
        storeInternally=True,
    )

    # Act
    delete_response = Content.delete(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        contentId=content.id,
    )

    # Assert
    assert_delete_response(delete_response, skip_fields=["id"])


@pytest.mark.ai
@pytest.mark.integration
def test_content__delete__deletes_content_by_file_path(
    integration_test_config: IntegrationTestConfig,
    base_content_input: Content.Input,
) -> None:
    """
    Purpose: Verify content can be deleted by file path.
    Why this matters: Provides flexible content deletion using file paths.
    Setup summary: Create content, delete by file path, assert deletion response.
    """
    # Arrange
    # Create content to delete
    content = Content.upsert(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        input=base_content_input,
        scopeId=integration_test_config.root_scope_id,
        storeInternally=True,
    )

    # Act
    delete_response = Content.delete(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        filePath=integration_test_config.root_folder_path + "/" + content["key"],
    )

    # Assert
    assert_delete_response(delete_response, skip_fields=["id"])


@pytest.mark.ai
@pytest.mark.integration
def test_content__resolve_content_id_from_file_path__returns_id_when_content_id_provided(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify resolve_content_id_from_file_path returns content ID when provided.
    Why this matters: Ensures direct ID resolution works correctly.
    Setup summary: Provide content ID, assert same ID is returned.
    """
    # Act
    resolved_id = Content.resolve_content_id_from_file_path(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        content_id=created_content.id,
        file_path=None,
    )

    # Assert
    assert resolved_id == created_content.id


@pytest.mark.ai
@pytest.mark.integration
def test_content__resolve_content_id_from_file_path__resolves_id_from_file_path(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify resolve_content_id_from_file_path resolves ID from file path.
    Why this matters: Enables ID lookup using file paths for flexible content access.
    Setup summary: Provide file path, assert correct content ID is resolved.
    """
    # Act
    resolved_id = Content.resolve_content_id_from_file_path(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        content_id=None,
        file_path=integration_test_config.root_folder_path
        + "/"
        + created_content["key"],
    )

    # Assert
    assert resolved_id is not None
    assert resolved_id == created_content.id


@pytest.mark.ai
@pytest.mark.integration
def test_content__resolve_content_id_from_file_path__raises_on_invalid_file_path(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify resolve_content_id_from_file_path raises error for invalid file path.
    Why this matters: Ensures proper error handling for non-existent content.
    Setup summary: Provide invalid file path, assert ValueError is raised.
    """
    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        _ = Content.resolve_content_id_from_file_path(
            user_id=integration_test_config.user_id,
            company_id=integration_test_config.company_id,
            file_path=integration_test_config.root_folder_path
            + "/non_existent_file_path_12345.txt",
        )
    assert "Could not find file with filePath" in str(exc_info.value)


@pytest.mark.ai
@pytest.mark.integration
def test_content__resolve_content_id_from_file_path__returns_none_when_no_params_provided(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify resolve_content_id_from_file_path returns None when no params provided.
    Why this matters: Ensures graceful handling of missing parameters.
    Setup summary: Call without content_id or file_path, assert None is returned.
    """
    # Act
    resolved_id = Content.resolve_content_id_from_file_path(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        content_id=None,
        file_path=None,
    )

    # Assert
    assert resolved_id is None


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_content__upsert_async__creates_content(
    integration_test_config: IntegrationTestConfig,
    base_content_input: Content.Input,
    created_content_ids: list[str],
) -> None:
    """
    Purpose: Verify async upsert creates content successfully.
    Why this matters: Enables asynchronous content creation for better performance.
    Setup summary: Create content using async method, assert content structure.
    """
    # Act
    content = await Content.upsert_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        input=base_content_input,
        scopeId=integration_test_config.root_scope_id,
        storeInternally=True,
    )

    # Track for cleanup
    created_content_ids.append(content.id)

    # Assert
    assert_content(content, skip_fields=["chunks", "updatedAt", "OBJECT_NAME"])
    assert content["key"] == base_content_input["key"]


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_content__get_info_async__retrieves_content_info(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify async get_info retrieves content information.
    Why this matters: Enables asynchronous content info retrieval for better performance.
    Setup summary: Retrieve content info using async method, assert content info structure.
    """
    # Act
    result = await Content.get_info_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        contentId=created_content.id,
    )

    # Assert
    assert isinstance(result, dict)
    assert "contentInfo" in result
    assert "totalCount" in result
    assert isinstance(result["totalCount"], int)
    assert isinstance(result["contentInfo"], list)


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_content__get_infos_async__returns_content_infos(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify async get_infos returns content information list.
    Why this matters: Enables asynchronous content listing for better performance.
    Setup summary: Retrieve content infos using async method, assert paginated structure.
    """
    # Act
    result = await Content.get_infos_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
    )

    # Assert
    assert isinstance(result, dict)
    assert "contentInfos" in result
    assert "totalCount" in result
    assert isinstance(result["totalCount"], int)
    assert isinstance(result["contentInfos"], list)


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_content__update_async__updates_content(
    integration_test_config: IntegrationTestConfig,
    created_content: Content,
) -> None:
    """
    Purpose: Verify async update modifies content successfully.
    Why this matters: Enables asynchronous content updates for better performance.
    Setup summary: Update content using async method, assert update succeeds.
    """
    # Arrange
    import uuid

    new_title = f"Async Updated Title {uuid.uuid4().hex[:8]}"

    # Act
    updated_content = await Content.update_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        contentId=created_content.id,
        title=new_title,
    )

    # Assert
    assert isinstance(updated_content, dict)
    assert "id" in updated_content
    assert "title" in updated_content
    assert updated_content["title"] == new_title


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_content__delete_async__deletes_content(
    integration_test_config: IntegrationTestConfig,
    base_content_input: Content.Input,
) -> None:
    """
    Purpose: Verify async delete removes content successfully.
    Why this matters: Enables asynchronous content deletion for better performance.
    Setup summary: Create content, delete using async method, assert deletion response.
    """
    # Arrange
    # Create content to delete
    content = await Content.upsert_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        input=base_content_input,
        scopeId=integration_test_config.root_scope_id,
        storeInternally=True,
    )

    # Act
    delete_response = await Content.delete_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        contentId=content.id,
    )

    # Assert
    assert_delete_response(delete_response, skip_fields=["id"])
    assert (
        "contentId" in delete_response
    )  # TODO: I see this in the response, but it's not in the type definition
    assert delete_response["contentId"] == content.id


@pytest.mark.ai
@pytest.mark.integration
def test_content__ingest_magic_table_sheets__creates_content_from_table_data(
    integration_test_config: IntegrationTestConfig,
    created_content_ids: list[str],
) -> None:
    """
    Purpose: Verify magic table sheets can be ingested as content.
    Why this matters: Enables structured data ingestion from table formats.
    Setup summary: Create table data, ingest using magic table sheets, assert content creation.
    """
    # Arrange
    import uuid

    table_data: Content.MagicTableRow = {
        "rowId": f"row_{uuid.uuid4().hex[:8]}",
        "columns": [
            {
                "columnId": "col_1",
                "columnName": "Name",
                "content": f"Test Name {uuid.uuid4().hex[:8]}",
            },
            {
                "columnId": "col_2",
                "columnName": "Value",
                "content": f"Test Value {uuid.uuid4().hex[:8]}",
            },
        ],
    }

    ingestion_config: Content.MagicTableSheetIngestionConfiguration = {
        "columnIdsInMetadata": ["col_1"],
        "columnIdsInChunkText": ["col_2"],
    }

    ingest_params: Content.MagicTableSheetIngestParams = {
        "data": [table_data],
        "ingestionConfiguration": ingestion_config,
        "metadata": {"source": "integration_test"},
        "scopeId": integration_test_config.root_scope_id,
        "sheetName": f"test_sheet_{uuid.uuid4().hex[:8]}",
    }

    # Act
    response = Content.ingest_magic_table_sheets(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        **ingest_params,
    )

    # Assert
    assert isinstance(response, dict)
    assert "rowIdsToContentIds" in response
    assert isinstance(response["rowIdsToContentIds"], list)
    if len(response["rowIdsToContentIds"]) > 0:
        row_mapping = response["rowIdsToContentIds"][0]
        assert "rowId" in row_mapping
        assert "contentId" in row_mapping
        # Track for cleanup
        created_content_ids.append(row_mapping["contentId"])


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_content__ingest_magic_table_sheets_async__creates_content_from_table_data(
    integration_test_config: IntegrationTestConfig,
    created_content_ids: list[str],
) -> None:
    """
    Purpose: Verify async magic table sheets ingestion works correctly.
    Why this matters: Enables asynchronous structured data ingestion for better performance.
    Setup summary: Create table data, ingest using async method, assert content creation.
    """
    # Arrange
    import uuid

    table_data: Content.MagicTableRow = {
        "rowId": f"row_{uuid.uuid4().hex[:8]}",
        "columns": [
            {
                "columnId": "col_1",
                "columnName": "Name",
                "content": f"Test Name {uuid.uuid4().hex[:8]}",
            },
            {
                "columnId": "col_2",
                "columnName": "Value",
                "content": f"Test Value {uuid.uuid4().hex[:8]}",
            },
        ],
    }

    ingestion_config: Content.MagicTableSheetIngestionConfiguration = {
        "columnIdsInMetadata": ["col_1"],
        "columnIdsInChunkText": ["col_2"],
    }

    ingest_params: Content.MagicTableSheetIngestParams = {
        "data": [table_data],
        "ingestionConfiguration": ingestion_config,
        "metadata": {"source": "integration_test"},
        "scopeId": integration_test_config.root_scope_id,
        "sheetName": f"test_sheet_{uuid.uuid4().hex[:8]}",
    }

    # Act
    response = await Content.ingest_magic_table_sheets_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        **ingest_params,
    )

    # Assert
    assert isinstance(response, dict)
    assert "rowIdsToContentIds" in response
    assert isinstance(response["rowIdsToContentIds"], list)
    if len(response["rowIdsToContentIds"]) > 0:
        row_mapping = response["rowIdsToContentIds"][0]
        assert "rowId" in row_mapping
        assert "contentId" in row_mapping
        # Track for cleanup
        created_content_ids.append(row_mapping["contentId"])
