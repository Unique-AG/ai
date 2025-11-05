"""
Integration tests for the Folder API resource.

These tests make actual API calls and require valid credentials.
Configuration must be provided via tests/.env file.

Required environment variables in tests/.env:
- UNIQUE_TEST_API_KEY: API key for authentication
- UNIQUE_TEST_APP_ID: App ID for authentication
- UNIQUE_TEST_USER_ID: User ID for API requests
- UNIQUE_TEST_COMPANY_ID: Company ID for API requests

Required environment variables:
- UNIQUE_TEST_BASE_URL: Base URL for API
- UNIQUE_TEST_SCOPE_ID: Scope ID for testing get_info by scope ID
- UNIQUE_TEST_FOLDER_PATH: Folder path for testing get_info by path
"""

from __future__ import annotations

import pytest

from tests.test_config import IntegrationTestConfig
from unique_sdk.api_resources._folder import Folder


@pytest.mark.ai
@pytest.mark.integration
def test_folder__get_info__by_scope_id(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify folder information can be retrieved by scope ID.
    Why this matters: Core functionality for accessing folder metadata.
    Setup summary: Call get_info with scopeId, assert folder info structure.
    """
    # Act
    folder_info = Folder.get_info(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        scopeId=integration_test_config.root_scope_id,
    )

    # Assert
    assert isinstance(folder_info, dict)
    assert "id" in folder_info
    assert "name" in folder_info
    assert "ingestionConfig" in folder_info


@pytest.mark.ai
@pytest.mark.integration
def test_folder__get_info__by_folder_path(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify folder information can be retrieved by folder path.
    Why this matters: Provides flexible folder access using path strings.
    Setup summary: Call get_info with folderPath, assert folder info structure.
    """
    # Act
    folder_info = Folder.get_info(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        folderPath=integration_test_config.root_folder_path,
    )

    # Assert
    assert isinstance(folder_info, dict)
    assert "id" in folder_info
    assert "name" in folder_info
    assert "ingestionConfig" in folder_info


@pytest.mark.ai
@pytest.mark.integration
def test_folder__get_infos__returns_list(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify get_infos returns a list of folder information.
    Why this matters: Enables paginated folder listing functionality.
    Setup summary: Call get_infos without parentId to get root folders, assert list structure.
    """
    # Act
    result = Folder.get_infos(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
    )

    # Assert
    # Type annotation says get_infos returns List[Folder.FolderInfo]
    # We assume the type annotation is correct - if it's not, this will fail naturally
    assert isinstance(result, dict)
    assert isinstance(result["totalCount"], int)
    assert isinstance(result["folderInfos"], list)

    # If folders exist, verify structure
    if len(result["folderInfos"]) > 0:
        folder = result["folderInfos"][0]
        assert isinstance(folder, dict)
        assert "id" in folder
        assert "name" in folder
        assert "ingestionConfig" in folder


@pytest.mark.ai
@pytest.mark.integration
def test_folder__get_infos__with_pagination(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify get_infos supports pagination with take and skip parameters.
    Why this matters: Enables efficient handling of large folder collections.
    Setup summary: Call get_infos with take=5 and skip=0, assert paginated results.
    """
    # Act
    result = Folder.get_infos(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        take=5,
        skip=0,
    )

    # Assert
    # Type annotation says get_infos returns List[Folder.FolderInfo]
    # We assume the type annotation is correct - if it's not, this will fail naturally
    assert isinstance(result["totalCount"], int)
    assert isinstance(result["folderInfos"], list)


@pytest.mark.ai
@pytest.mark.integration
def test_folder__create_paths__creates_folder_structure(
    integration_test_config: IntegrationTestConfig,
    created_folders: list[str],
) -> None:
    """
    Purpose: Verify create_paths creates folder structure from path list.
    Why this matters: Core functionality for programmatic folder creation.
    Setup summary: Create test folder path, call create_paths, assert created folders.
    """
    # Arrange
    import uuid

    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]

    # Act
    response = Folder.create_paths(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )

    # Track for cleanup
    created_folders.append(test_path)

    # Assert
    assert isinstance(response, dict)
    assert "createdFolders" in response
    assert isinstance(response["createdFolders"], list)
    assert len(response["createdFolders"]) > 0
    created_folder = response["createdFolders"][0]
    assert "id" in created_folder
    assert "name" in created_folder
    assert "object" in created_folder
    assert created_folder["object"] == "folder"


@pytest.mark.ai
@pytest.mark.integration
def test_folder__update_ingestion_config__updates_config(
    integration_test_config: IntegrationTestConfig,
    created_folders: list[str],
) -> None:
    """
    Purpose: Verify ingestion config can be updated for a folder.
    Why this matters: Critical for configuring document ingestion behavior.
    Setup summary: Create test folder, update ingestion config, assert update succeeds.
    """
    # Arrange
    import uuid

    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]

    # Create folder first
    _ = Folder.create_paths(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )

    # Track for cleanup
    created_folders.append(test_path)

    ingestion_config: Folder.IngestionConfig = {
        "uniqueIngestionMode": "INGESTION",
        "chunkStrategy": "UNIQUE_DEFAULT_CHUNKING",
    }

    # Act
    updated_folder = Folder.update_ingestion_config(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        folderPath=test_path,
        ingestionConfig=ingestion_config,
        applyToSubScopes=False,
    )

    # Assert
    assert isinstance(updated_folder, dict)
    assert "id" in updated_folder


@pytest.mark.ai
@pytest.mark.integration
def test_folder__update__updates_folder_name(
    integration_test_config: IntegrationTestConfig,
    created_folders: list[str],
) -> None:
    """
    Purpose: Verify folder name can be updated.
    Why this matters: Enables folder renaming functionality.
    Setup summary: Create test folder, update name, assert name change.
    """
    # Arrange
    import uuid

    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]
    new_name = f"updated_name_{uuid.uuid4().hex[:8]}"

    # Create folder first
    _ = Folder.create_paths(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )

    # Track for cleanup
    created_folders.append(test_path)

    # Act
    updated_folder = Folder.update(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        folderPath=test_path,
        name=new_name,
    )

    # Assert
    assert isinstance(updated_folder, dict)
    assert "name" in updated_folder
    assert updated_folder["name"] == new_name


@pytest.mark.ai
@pytest.mark.integration
def test_folder__delete__removes_folder(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify folder can be deleted by path.
    Why this matters: Core functionality for folder management lifecycle.
    Setup summary: Create test folder, delete it, assert deletion response.
    """
    # Arrange
    import uuid

    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]

    # Create folder first
    _ = Folder.create_paths(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )

    # Act
    delete_response = Folder.delete(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        folderPath=test_path,
    )

    # Assert
    assert isinstance(delete_response, dict)
    assert "successFolders" in delete_response
    assert "failedFolders" in delete_response
    assert isinstance(delete_response["successFolders"], list)
    assert isinstance(delete_response["failedFolders"], list)


@pytest.mark.ai
@pytest.mark.integration
def test_folder__resolve_scope_id_from_folder_path__resolves_id(
    integration_test_config: IntegrationTestConfig,
    created_folders: list[str],
) -> None:
    """
    Purpose: Verify resolve_scope_id_from_folder_path resolves folder ID from path.
    Why this matters: Enables flexible folder identification method.
    Setup summary: Create test folder, resolve ID from path, assert ID matches.
    """
    # Arrange
    import uuid

    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]

    # Create folder first
    create_response = Folder.create_paths(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )
    created_folder_id = create_response["createdFolders"][0]["id"]

    # Track for cleanup
    created_folders.append(test_path)

    # Act
    resolved_id = Folder.resolve_scope_id_from_folder_path(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        folder_path=test_path,
    )

    # Assert
    assert resolved_id is not None
    assert resolved_id == created_folder_id


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_folder__get_info_async__retrieves_folder_info(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify async get_info retrieves folder information.
    Why this matters: Enables asynchronous folder operations for better performance.
    Setup summary: Call get_info_async, assert folder info structure.
    """
    # Act
    folder_info = await Folder.get_info_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        scopeId=integration_test_config.root_scope_id,
    )

    # Assert
    assert isinstance(folder_info, dict)
    assert "id" in folder_info
    assert "name" in folder_info


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_folder__get_infos_async__returns_list(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify async get_infos returns a list of folder information.
    Why this matters: Enables asynchronous paginated folder listing.
    Setup summary: Call get_infos_async, assert list structure.
    """
    # Act
    result = await Folder.get_infos_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
    )

    # Assert
    # Type annotation says get_infos returns List[Folder.FolderInfo]
    # We assume the type annotation is correct - if it's not, this will fail naturally
    assert isinstance(result, dict)
    assert "totalCount" in result
    assert "folderInfos" in result
    assert isinstance(result["totalCount"], int)
    assert isinstance(result["folderInfos"], list)


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_folder__create_paths_async__creates_folder_structure(
    integration_test_config: IntegrationTestConfig,
    created_folders: list[str],
) -> None:
    """
    Purpose: Verify async create_paths creates folder structure.
    Why this matters: Enables asynchronous programmatic folder creation.
    Setup summary: Create test folder path, call create_paths_async, assert created folders.
    """
    # Arrange
    import uuid

    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]

    # Act
    response = await Folder.create_paths_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )

    # Track for cleanup
    created_folders.append(test_path)

    # Assert
    assert isinstance(response, dict)
    assert "createdFolders" in response
    assert isinstance(response["createdFolders"], list)


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_folder__update_ingestion_config_async__updates_config(
    integration_test_config: IntegrationTestConfig,
    created_folders: list[str],
) -> None:
    """
    Purpose: Verify async ingestion config update functionality.
    Why this matters: Enables asynchronous configuration of document ingestion.
    Setup summary: Create test folder, update ingestion config async, assert update succeeds.
    """
    # Arrange
    import uuid

    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]

    # Create folder first
    _ = await Folder.create_paths_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )

    # Track for cleanup
    created_folders.append(test_path)

    ingestion_config: Folder.IngestionConfig = {
        "uniqueIngestionMode": "INGESTION",
        "chunkStrategy": "UNIQUE_DEFAULT_CHUNKING",
    }

    # Act
    updated_folder = await Folder.update_ingestion_config_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        folderPath=test_path,
        ingestionConfig=ingestion_config,
        applyToSubScopes=False,
    )

    # Assert
    assert isinstance(updated_folder, dict)
    assert "id" in updated_folder


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_folder__delete_async__removes_folder(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Purpose: Verify async folder deletion functionality.
    Why this matters: Enables asynchronous folder lifecycle management.
    Setup summary: Create test folder, delete it async, assert deletion response.
    """
    # Arrange
    import uuid

    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]

    # Create folder first
    _ = await Folder.create_paths_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )

    # Act
    delete_response = await Folder.delete_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        folderPath=test_path,
    )

    # Assert
    assert isinstance(delete_response, dict)
    assert "successFolders" in delete_response
    assert "failedFolders" in delete_response


@pytest.mark.ai
@pytest.mark.integration
def test_folder__create_and_verify_after_wait__folder_exists(
    integration_test_config: IntegrationTestConfig,
    created_folders: list[str],
) -> None:
    """
    Purpose: Verify folder creation with a wait time before verification.
    Why this matters: Tests eventual consistency and folder availability after creation.
    Setup summary: Create folder, wait, then verify it exists with get_info.
    """
    import time
    import uuid

    # Arrange
    # Create folder path relative to root folder
    root_path = integration_test_config.root_folder_path.rstrip("/")
    test_path = f"{root_path}/test/integration/{uuid.uuid4().hex[:8]}"
    paths = [test_path]

    # Act: Create folder
    create_response = Folder.create_paths(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        paths=paths,
    )

    # Track for cleanup
    created_folders.append(test_path)

    # Assert: Verify creation response
    assert isinstance(create_response, dict)
    assert "createdFolders" in create_response
    assert len(create_response["createdFolders"]) > 0
    created_folder_id = create_response["createdFolders"][0]["id"]

    # Wait a bit for the folder to be available
    wait_time = 1.0  # 1 second wait time
    time.sleep(wait_time)

    # Verify folder exists by getting its info
    folder_info = Folder.get_info(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        folderPath=test_path,
    )

    # Assert: Verify folder info matches created folder
    assert isinstance(folder_info, dict)
    assert "id" in folder_info
    assert folder_info["id"] == created_folder_id
    assert "name" in folder_info
