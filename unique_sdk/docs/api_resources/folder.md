# Folder API

The Folder API manages the hierarchical organization of content in the Unique AI knowledge base.

## Overview

Organize content into folder structures with:

- Folder creation and management
- Access control
- Ingestion configuration
- Path-based or ID-based operations

## Methods

??? example "`unique_sdk.Folder.get_info` - Get folder information"

    Get folder information by scope ID or path.

    **Parameters:**

    - `scopeId` (str, optional) - Folder scope ID (required if `folderPath` not provided)
    - `folderPath` (str, optional) - Folder path (required if `scopeId` not provided)

    **Returns:**

    Returns a [`FolderInfo`](#folderinfo) object.

    **Example - By Scope ID:**

    ```python
    folder = unique_sdk.Folder.get_info(
        user_id=user_id,
        company_id=company_id,
        scopeId="scope_w78wfn114va9o22s13r03yq"
    )
    ```

    **By Path:**

    ```python
    folder = unique_sdk.Folder.get_info(
        user_id=user_id,
        company_id=company_id,
        folderPath="/Company/Atlas/Due Diligence/Arch"
    )
    ```

??? example "`unique_sdk.Folder.get_folder_path` - Get folder path"

    !!! info "Compatibility"
        Compatible with release >.48

    Get the complete folder path for a scope ID.

    **Parameters:**

    - `scope_id` (str, required) - Folder scope ID

    **Returns:**

    Returns a [`FolderPathResponse`](#folderpathresponse) object.

    **Example:**

    ```python
    path = unique_sdk.Folder.get_folder_path(
        user_id=user_id,
        company_id=company_id,
        scope_id="scope_w78wfn114va9o22s13r03yq"
    )

    print(path)  # "/company/subfolder1/subfolder2"
    ```

??? example "`unique_sdk.Folder.get_infos` - Get paginated folders list"

    Get paginated list of folders, optionally filtered by parent.

    **Parameters:**

    - `parentId` (str, optional) - Parent folder ID (if not provided, returns root folders)
    - `parentFolderPath` (str, optional) - Parent folder path (alternative to `parentId`)
    - `skip` (int, optional) - Number of folders to skip (default: 0)
    - `take` (int, optional) - Number of folders to return

    **Returns:**

    Returns a [`FolderInfos`](#folderinfos) object.

    **Example - Get All Root Folders:**

    ```python
    folders = unique_sdk.Folder.get_infos(
        user_id=user_id,
        company_id=company_id,
        take=10,
        skip=0
    )
    ```

    **Get Subfolders by ID:**

    ```python
    subfolders = unique_sdk.Folder.get_infos(
        user_id=user_id,
        company_id=company_id,
        parentId="scope_s18seqpnltf35niydg77xgyp",
        take=10,
        skip=0
    )
    ```

    **Get Subfolders by Path:**

    ```python
    subfolders = unique_sdk.Folder.get_infos(
        user_id=user_id,
        company_id=company_id,
        parentFolderPath="/Company/Reports",
        take=10,
        skip=0
    )
    ```

??? example "`unique_sdk.Folder.create_paths` - Create folder paths"

    Create multiple folder paths at once. Creates missing folders in the path.

    **Parameters:**

    - `paths` (List[str], optional) - List of full folder paths starting from root. Either this or `parentScopeId` + `relativePaths` must be provided.
    - `parentScopeId` (str, optional) - Parent scope ID to create folders under. Must be provided together with `relativePaths`.
    - `relativePaths` (List[str], optional) - List of relative paths to create under `parentScopeId`. Must be provided together with `parentScopeId`. Each path must not start with `/` and cannot be empty.
    - `inheritAccess` (bool, optional) - Whether to inherit access permissions from parent folders (default: `True`)

    **Returns:**

    Returns a [`CreateFolderStructureResponse`](#createfolderstructureresponse) object.

    **Example - Basic Creation with Full Paths:**

    ```python
    unique_sdk.Folder.create_paths(
        user_id=user_id,
        company_id=company_id,
        paths=[
            "/Company/Reports/Q1",
            "/Company/Reports/Q2",
            "/Company/Policies"
        ]
    )
    ```

    **Create Folders by Scope:**

    ```python
    unique_sdk.Folder.create_paths(
        user_id=user_id,
        company_id=company_id,
        parentScopeId="scope_fctg9an96pixkij6da9rwaiw",
        relativePaths=[
            "subject/date",
            "another-folder"
        ]
    )
    ```

    **Without Inheriting Access:**

    ```python
    unique_sdk.Folder.create_paths(
        user_id=user_id,
        company_id=company_id,
        paths=[
            "/Company/Reports/Q1",
            "/Company/Reports/Q2"
        ],
        inheritAccess=False
    )
    ```

??? example "`unique_sdk.Folder.update` - Update folder properties"

    Update folder properties: name or parent folder.

    **Parameters:**

    - `scopeId` (str, optional) - Folder scope ID (required if `folderPath` not provided)
    - `folderPath` (str, optional) - Folder path (required if `scopeId` not provided)
    - `name` (str, optional) - New folder name
    - `parentId` (str | None, optional) - New parent folder ID (use `None` to move to root)
    - `parentFolderPath` (str, optional) - New parent folder path

    **Returns:**

    Returns a [`Folder`](#folder) object.

    **Example - Move to New Parent by Path:**

    ```python
    unique_sdk.Folder.update(
        user_id=user_id,
        company_id=company_id,
        scopeId="scope_dwekjnf3330woioppm",
        parentFolderPath="/Company/folder1/folder2"
    )
    ```

    **Move and Rename:**

    ```python
    unique_sdk.Folder.update(
        user_id=user_id,
        company_id=company_id,
        folderPath="/Company/folder1",
        parentId="scope_dweekjrfhirtuhgroppm",
        name="January"
    )
    ```

    **Move to Root:**

    ```python
    unique_sdk.Folder.update(
        user_id=user_id,
        company_id=company_id,
        folderPath="/Company/folder1",
        parentId=None,  # Move to root
        name="January"
    )
    ```

??? example "`unique_sdk.Folder.delete` - Delete folder"

    !!! info "Compatibility"
        Compatible with release >.36

    Delete a folder by scope ID or path.

    **Parameters:**

    - `scopeId` (str, optional) - Folder scope ID (required if `folderPath` not provided)
    - `folderPath` (str, optional) - Folder path (required if `scopeId` not provided)
    - `recursive` (bool, optional) - Delete subfolders and contents (like `rm -rf`)

    **Returns:**

    Returns a [`DeleteResponse`](#deleteresponse) object.

    **Example - Non-Recursive Delete (Empty Folders Only):**

    ```python
    unique_sdk.Folder.delete(
        user_id=user_id,
        company_id=company_id,
        folderPath="/Company/Atlas/Due Diligence/Arch"
    )
    ```

    **Recursive Delete:**

    ```python
    result = unique_sdk.Folder.delete(
        user_id=user_id,
        company_id=company_id,
        scopeId="scope_w78wfn114va9o22s13r03yq",
        recursive=True
    )

    print(f"Deleted: {result.successFolders}")
    print(f"Failed: {result.failedFolders}")
    ```

??? example "`unique_sdk.Folder.update_ingestion_config` - Update ingestion config"

    Update ingestion configuration for a folder and optionally its subfolders.

    **Parameters:**

    - `scopeId` (str, optional) - Folder scope ID (required if `folderPath` not provided)
    - `folderPath` (str, optional) - Folder path (required if `scopeId` not provided)
    - `ingestionConfig` (IngestionConfig, required) - Ingestion configuration. See [`Folder.IngestionConfig`](#folderingestionconfig) for structure.
    - `applyToSubScopes` (bool, required) - Whether to apply config to subfolders

    **Returns:**

    Returns a [`Folder`](#folder) object.

    **Example - By Scope ID:**

    ```python
    unique_sdk.Folder.update_ingestion_config(
        user_id=user_id,
        company_id=company_id,
        scopeId="scope_qbnkde820dbmuw2900",
        ingestionConfig={
            "uniqueIngestionMode": "INGESTION",
            "chunkStrategy": "UNIQUE_DEFAULT_CHUNKING",
            "chunkMaxTokens": 1000
        },
        applyToSubScopes=True
    )
    ```

    **By Path:**

    ```python
    unique_sdk.Folder.update_ingestion_config(
        user_id=user_id,
        company_id=company_id,
        folderPath="/Company/folder1/folder2",
        ingestionConfig={
            "uniqueIngestionMode": "INGESTION",
            "chunkStrategy": "UNIQUE_DEFAULT_CHUNKING"
        },
        applyToSubScopes=True
    )
    ```

??? example "`unique_sdk.Folder.add_access` - Grant access permissions"

    Grant access permissions to a folder.

    **Parameters:**

    - `scopeId` (str, optional) - Folder scope ID (required if `folderPath` not provided)
    - `folderPath` (str, optional) - Folder path (required if `scopeId` not provided)
    - `scopeAccesses` (List[ScopeAccess], required) - List of access permissions. See [`Folder.ScopeAccess`](#folderscopeaccess) for structure.
    - `applyToSubScopes` (bool, required) - Whether to apply access to subfolders

    **Returns:**

    Returns a [`Folder`](#folder) object.

    **Example - Add Group Access:**

    ```python
    unique_sdk.Folder.add_access(
        user_id=user_id,
        company_id=company_id,
        scopeId="scope_231e4kjn4foffww34",
        scopeAccesses=[
            {
                "entityId": "group_id",
                "type": "WRITE",  # or "READ"
                "entityType": "GROUP"  # or "USER"
            }
        ],
        applyToSubScopes=True
    )
    ```

    **By Path:**

    ```python
    unique_sdk.Folder.add_access(
        user_id=user_id,
        company_id=company_id,
        folderPath="/Company/folder1/folder2",
        scopeAccesses=[
            {
                "entityId": "group_id",
                "type": "WRITE",
                "entityType": "GROUP"
            }
        ],
        applyToSubScopes=True
    )
    ```

??? example "`unique_sdk.Folder.remove_access` - Revoke access permissions"

    Revoke access permissions from a folder.

    **Parameters:**

    - `scopeId` (str, optional) - Folder scope ID (required if `folderPath` not provided)
    - `folderPath` (str, optional) - Folder path (required if `scopeId` not provided)
    - `scopeAccesses` (List[ScopeAccess], required) - List of access permissions to remove. See [`Folder.ScopeAccess`](#folderscopeaccess) for structure.
    - `applyToSubScopes` (bool, required) - Whether to remove access from subfolders

    **Returns:**

    Returns a [`Folder`](#folder) object or `dict`.

    **Example - By Scope ID:**

    ```python
    unique_sdk.Folder.remove_access(
        user_id=user_id,
        company_id=company_id,
        scopeId="scope_dwekjnf3330woioppm",
        scopeAccesses=[
            {
                "entityId": "group_id",
                "type": "WRITE",
                "entityType": "GROUP"
            }
        ],
        applyToSubScopes=True
    )
    ```

    **By Path:**

    ```python
    unique_sdk.Folder.remove_access(
        user_id=user_id,
        company_id=company_id,
        folderPath="/Company/folder1/folder2",
        scopeAccesses=[
            {
                "entityId": "group_id",
                "type": "WRITE",
                "entityType": "GROUP"
            }
        ],
        applyToSubScopes=True
    )
    ```

## Use Cases

??? example "Organize Knowledge Base"

    ```python
    # Create department structure
    departments = [
        "/Company/Engineering/Backend",
        "/Company/Engineering/Frontend",
        "/Company/Sales/NA",
        "/Company/Sales/EU",
        "/Company/HR/Policies"
    ]

    unique_sdk.Folder.create_paths(
        user_id=user_id,
        company_id=company_id,
        paths=departments
    )

    # Configure ingestion for engineering docs
    unique_sdk.Folder.update_ingestion_config(
        user_id=user_id,
        company_id=company_id,
        folderPath="/Company/Engineering",
        ingestionConfig={
            "uniqueIngestionMode": "INGESTION",
            "chunkStrategy": "UNIQUE_DEFAULT_CHUNKING",
            "chunkMaxTokens": 1500  # Larger chunks for technical docs
        },
        applyToSubScopes=True
    )
    ```

??? example "Bulk Permission Management"

    ```python
    def grant_team_access(team_id, folder_paths):
        """Grant team access to multiple folders."""
        for path in folder_paths:
            try:
                unique_sdk.Folder.add_access(
                    user_id=user_id,
                    company_id=company_id,
                    folderPath=path,
                    scopeAccesses=[{
                        "entityId": team_id,
                        "type": "READ",
                        "entityType": "GROUP"
                    }],
                    applyToSubScopes=True
                )
                print(f"✓ Access granted: {path}")
            except Exception as e:
                print(f"✗ Failed: {path} - {e}")

    grant_team_access("group_sales_team", [
        "/Company/Sales",
        "/Company/Marketing"
    ])
    ```

??? example "Navigate Folder Tree"

    ```python
    def list_folder_tree(parent_id=None, indent=0):
        """Recursively list folder structure."""
        folders = unique_sdk.Folder.get_infos(
            user_id=user_id,
            company_id=company_id,
            parentId=parent_id,
            take=100
        )
        
        for folder in folders.folderInfos:
            print("  " * indent + f"📁 {folder.name}")
            # Recursively list subfolders
            list_folder_tree(folder.id, indent + 1)

    # Print entire tree
    list_folder_tree()
    ```

## Best Practices

??? example "Use Paths for Readability"

    ```python
    # More readable and maintainable
    unique_sdk.Folder.update(
        folderPath="/Company/Q1_Reports",
        parentFolderPath="/Company/Archive/2024"
    )

    # vs scope IDs (harder to read)
    unique_sdk.Folder.update(
        scopeId="scope_abc123",
        parentId="scope_def456"
    )
    ```

??? example "Apply Configs to Subfolders"

    ```python
    # Set config once at parent level
    unique_sdk.Folder.update_ingestion_config(
        folderPath="/Company/Legal",
        ingestionConfig={
            "uniqueIngestionMode": "INGESTION",
            "chunkStrategy": "UNIQUE_DEFAULT_CHUNKING",
            "chunkMaxTokens": 2000  # Legal docs need larger chunks
        },
        applyToSubScopes=True  # Applies to all subfolders
    )
    ```

??? example "Handle Deletion Failures"

    ```python
    result = unique_sdk.Folder.delete(
        user_id=user_id,
        company_id=company_id,
        scopeId=scope_id,
        recursive=True
    )

    if result.failedFolders:
        print("Failed to delete (no write access):")
        for folder in result.failedFolders:
            print(f"  - {folder}")
    ```

## Input Types

#### Folder.ScopeAccess {#folderscopeaccess}

??? note "The `Folder.ScopeAccess` type defines access permissions for a folder"

    **Fields:**

    - `entityId` (str, required) - User or group ID
    - `type` (Literal["READ", "WRITE"], required) - Access type
    - `entityType` (Literal["USER", "GROUP"], required) - Entity type
    - `createdAt` (str, optional) - Creation timestamp (ISO 8601)

    **Used in:** `Folder.add_access()`, `Folder.remove_access()`

#### Folder.IngestionConfig {#folderingestionconfig}

??? note "The `Folder.IngestionConfig` type defines ingestion configuration for a folder"

    **Fields:**

    - `uniqueIngestionMode` (str, required) - Ingestion mode (e.g., "standard")
    - `chunkStrategy` (str, optional) - Chunking strategy (e.g., "default")
    - `chunkMaxTokens` (int, optional) - Maximum tokens per chunk
    - `chunkMaxTokensOnePager` (int, optional) - Maximum tokens for one-page documents
    - `chunkMinTokens` (int, optional) - Minimum tokens per chunk
    - `documentMinTokens` (int, optional) - Minimum tokens per document
    - `excelReadMode` (str, optional) - Excel reading mode
    - `jpgReadMode` (str, optional) - JPG reading mode
    - `pdfReadMode` (str, optional) - PDF reading mode
    - `pptReadMode` (str, optional) - PowerPoint reading mode
    - `wordReadMode` (str, optional) - Word document reading mode
    - `customApiOptions` (List[CustomApiOptions], optional) - Custom API options
    - `vttConfig` (VttConfig, optional) - VTT configuration

    **Used in:** `Folder.update_ingestion_config()`

## Return Types

#### Folder {#folder}

??? note "The `Folder` object represents a folder in the knowledge base"

    **Fields:**

    - `id` (str) - Unique folder identifier (scope ID)
    - `name` (str) - Folder name
    - `scopeAccess` (List[ScopeAccess]) - List of access permissions. See [`Folder.ScopeAccess`](#folderscopeaccess) for structure.
    - `children` (List[Children]) - List of child folders. See [`Folder.Children`](#folderchildren) for structure.

    **Returned by:** `Folder.update()`, `Folder.update_ingestion_config()`, `Folder.add_access()`, `Folder.remove_access()`

#### Folder.Children {#folderchildren}

??? note "The `Folder.Children` type represents a child folder"

    **Fields:**

    - `id` (str) - Child folder ID
    - `name` (str) - Child folder name

    **Used in:** `Folder.children`

#### Folder.FolderInfo {#folderinfo}

??? note "The `FolderInfo` object represents folder information"

    **Fields:**

    - `id` (str) - Unique folder identifier
    - `name` (str) - Folder name
    - `ingestionConfig` (IngestionConfig) - Ingestion configuration. See [`Folder.IngestionConfig`](#folderingestionconfig) for structure.
    - `createdAt` (str | None) - Creation timestamp (ISO 8601)
    - `updatedAt` (str | None) - Last update timestamp (ISO 8601)
    - `parentId` (str | None) - Parent folder ID
    - `externalId` (str | None) - External system identifier

    **Returned by:** `Folder.get_info()`

#### Folder.FolderInfos {#folderinfos}

??? note "The `FolderInfos` object contains paginated folder information"

    **Fields:**

    - `folderInfos` (List[FolderInfo]) - List of folder info objects. See [`Folder.FolderInfo`](#folderinfo) for structure.
    - `totalCount` (int) - Total number of matching folders

    **Returned by:** `Folder.get_infos()`

#### Folder.FolderPathResponse {#folderpathresponse}

??? note "The `FolderPathResponse` object contains a folder path"

    **Fields:**

    - `folderPath` (str) - Complete folder path

    **Returned by:** `Folder.get_folder_path()`

#### Folder.CreateFolderStructureResponse {#createfolderstructureresponse}

??? note "The `CreateFolderStructureResponse` object contains created folder information"

    **Fields:**

    - `createdFolders` (List[CreatedFolder]) - List of created folders. See [`Folder.CreatedFolder`](#foldercreatedfolder) for structure.

    **Returned by:** `Folder.create_paths()`

#### Folder.CreatedFolder {#foldercreatedfolder}

??? note "The `CreatedFolder` object represents a newly created folder"

    **Fields:**

    - `id` (str) - Folder ID
    - `object` (str) - Object type identifier
    - `name` (str) - Folder name
    - `parentId` (str | None) - Parent folder ID

    **Used in:** `CreateFolderStructureResponse.createdFolders`

#### Folder.DeleteResponse {#deleteresponse}

??? note "The `DeleteResponse` object contains deletion results"

    **Fields:**

    - `successFolders` (List[DeleteFolderResponse]) - List of successfully deleted folders. See [`Folder.DeleteFolderResponse`](#folderdeletefolderresponse) for structure.
    - `failedFolders` (List[DeleteFolderResponse]) - List of failed deletions. See [`Folder.DeleteFolderResponse`](#folderdeletefolderresponse) for structure.

    **Returned by:** `Folder.delete()`

#### Folder.DeleteFolderResponse {#folderdeletefolderresponse}

??? note "The `DeleteFolderResponse` object represents a deletion result for a single folder"

    **Fields:**

    - `id` (str) - Folder ID
    - `name` (str) - Folder name
    - `path` (str) - Folder path
    - `failReason` (str, optional) - Failure reason if deletion failed

    **Used in:** `DeleteResponse.successFolders`, `DeleteResponse.failedFolders`

## Related Resources

- [Content API](content.md) - Manage files within folders
- [Group API](group.md) - Manage group permissions
- [User API](user.md) - Manage user permissions

