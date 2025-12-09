# Content API

The Content API allows you to manage documents and files in the Unique AI knowledge base.

## Overview

The Content resource provides methods to:

- Search and retrieve content from the knowledge base
- Upload new documents and files
- Update existing content (title, location, metadata)
- Delete content
- Ingest magic table sheets

## Methods

??? example "`unique_sdk.Content.search` - Search content with filtering"

    Load full content/files from the knowledge base with user rights and filtering.
    
    **Returns:**

    Returns a list of [`Content`](#content) objects.

    **Parameters:**

    - `where` (required) - Filter conditions using [`ContentWhereInput`](#contentwhereinput)
    - `chatId` (optional) - Filter content by chat ID
    - `includeFailedContent` (optional) - Include failed ingestion content

    **Example:**

    ```python
    unique_sdk.Content.search(
        user_id=userId,
        company_id=companyId,
        where={
            "OR": [
                {
                    "title": {
                        "contains": "42",
                    },
                },
                {
                    "key": {
                        "contains": "42",
                    },
                },
            ],
        },
        chatId=chatId,
    )
    ```

??? example "`unique_sdk.Content.get_info` - Get content info (Deprecated)"

    !!! warning "Deprecated"
        Use `unique_sdk.Content.get_infos` instead.

    Get content info with UniqueQL metadata filtering.

    **Parameters:**

    - `metadataFilter` (optional) - UniqueQL metadata filter
    - `skip` (optional) - Number of entries to skip (default: 0)
    - `take` (optional) - Number of entries to return (default: 50)
    - `filePath` (optional) - Filter by file path
    - `contentId` (optional) - Filter by content ID
    - `chatId` (optional) - Filter by chat ID

    **Returns:**

    Returns a [`PaginatedContentInfo`](#paginatedcontentinfo) object.

    **Example:**

    ```python
    content_info_result = unique_sdk.Content.get_info(
        user_id=user_id,
        company_id=company_id,
        metadataFilter={
            "or": [
                {
                    "and": [
                        {
                            "operator": "contains",
                            "path": ["folderIdPath"],
                            "value": "uniquepathid://scope_abcdibgznc4bkdcx120zm5d"
                        },
                        {
                            "operator": "contains",
                            "path": ["title"],
                            "value": "ai"
                        }
                    ]
                }
            ]
        },
        skip=0,
        take=3,
    )
    ```

??? example "`unique_sdk.Content.get_infos` - Get content infos"

    Get content infos with either UniqueQL metadata filter or parentId. Cannot use both simultaneously.

    **Parameters:**

    - `metadataFilter` (optional) - UniqueQL metadata filter (cannot be used with `parentId`)
    - `parentId` (optional) - Filter by parent folder/scope ID (cannot be used with `metadataFilter`)
    - `skip` (optional) - Number of entries to skip (default: 0)
    - `take` (optional) - Number of entries to return (default: 50)

    **Returns:**

    Returns a [`PaginatedContentInfos`](#paginatedcontentinfos) object.

    **Example with Metadata Filter:**

    ```python
    content_info_result = unique_sdk.Content.get_infos(
        user_id=user_id,
        company_id=company_id,
        metadataFilter={
            "or": [
                {
                    "and": [
                        {
                            "operator": "contains",
                            "path": ["folderIdPath"],
                            "value": "uniquepathid://scope_abcdibgznc4bkdcx120zm5d"
                        },
                        {
                            "operator": "contains",
                            "path": ["title"],
                            "value": "ai"
                        }
                    ]
                }
            ]
        },
        skip=0,
        take=3,
    )
    ```

    **Example with Parent ID:**

    ```python
    content_info_result = unique_sdk.Content.get_infos(
        user_id=user_id,
        company_id=company_id,
        parentId="scope_ahefgj389srjbfejkkk98u"
    )
    ```

??? example "`unique_sdk.Content.upsert` - Upload content"

    Upload new content to the knowledge base into a specific scope or chat.

    **Parameters:**

    - `input` (required) - Content input object. See [`Content.Input`](#contentinput) for field details.
    - `scopeId` (str, optional) - Scope ID to upload to (required if `chatId` not provided)
    - `chatId` (str, optional) - Chat ID to upload to (required if `scopeId` not provided)
    - `sourceOwnerType` (str, optional) - Source owner type
    - `storeInternally` (bool, optional) - Store file internally
    - `fileUrl` (str, optional) - External file URL
    - `readUrl` (str, optional) - Read URL for confirming upload (used in second call)

    **Returns:**

    Returns a [`Content`](#content) object.

    **Example:**

    ```python
    import os
    import requests

    def upload_file(
        userId,
        companyId,
        path_to_file,
        displayed_filename,
        mimeType,
        scope_or_unique_path,
        description=None,
        ingestion_config=None,
        metadata=None,
    ):
        size = os.path.getsize(path_to_file)
        
        # Step 1: Create content and get upload URL
        createdContent = unique_sdk.Content.upsert(
            user_id=userId,
            company_id=companyId,
            input={
                "key": displayed_filename,
                "title": displayed_filename,
                "mimeType": mimeType,
                "description": description,
                "ingestionConfig": ingestion_config,
                "metadata": metadata,
            },
            scopeId=scope_or_unique_path,
        )

        uploadUrl = createdContent.writeUrl

        # Step 2: Upload to Azure blob storage
        with open(path_to_file, "rb") as file:
            requests.put(
                uploadUrl,
                data=file,
                headers={
                    "X-Ms-Blob-Content-Type": mimeType,
                    "X-Ms-Blob-Type": "BlockBlob",
                },
            )

        # Step 3: Confirm upload with file size
        unique_sdk.Content.upsert(
            user_id=userId,
            company_id=companyId,
            input={
                "key": displayed_filename,
                "title": displayed_filename,
                "mimeType": mimeType,
                "description": description,
                "byteSize": size,
                "ingestionConfig": ingestion_config,
                "metadata": metadata,
            },
            scopeId=scope_or_unique_path,
            readUrl=createdContent.readUrl,
        )

        return createdContent

    # Usage
    createdContent = upload_file(
        userId,
        companyId,
        "/path/to/file.pdf",
        "test.pdf",
        "application/pdf",
        "scope_stcj2osgbl722m22jayidx0n",
        ingestionConfig={
            "chunkMaxTokens": 1000,
            "uniqueIngestionMode": "INGESTION",
            "chunkStrategy": "UNIQUE_DEFAULT_CHUNKING"
        },
        metadata={
            "folderIdPath": "uniquepathid://scope_id"
        }
    )
    ```

??? example "`unique_sdk.Content.ingest_magic_table_sheets` - Ingest table sheets"

    Ingest a magic table sheet where each row is processed and converted into content.

    **Parameters:**

    - `data` (List[MagicTableSheetTable], required) - List of table rows to ingest
      - Each row contains:
        - `rowId` (str) - Unique row identifier
        - `columns` (List[MagicTableSheetTableColumn]) - List of column values
          - `columnId` (str) - Column identifier
          - `columnName` (str) - Column name
          - `content` (str) - Column content/text
    - `ingestionConfiguration` (MagicTableSheetIngestionConfiguration, required) - Configuration for ingestion
      - `columnIdsInMetadata` (List[str]) - Column IDs to include in metadata
      - `columnIdsInChunkText` (List[str]) - Column IDs to include in chunk text
    - `metadata` (Dict[str, Optional[str]], required) - Base metadata for all ingested content
    - `scopeId` (str, required) - Scope ID to ingest content into
    - `sheetName` (str, required) - Name of the sheet being ingested

    **Returns:**

    Returns a [`MagicTableSheetResponse`](#magictablesheetresponse) object.

    **Example:**

    ```python
    params = {
        "user_id": user_id,
        "company_id": company_id,
        "data": [
            {
                "rowId": "2",
                "columns": [
                    {"columnId": "0", "columnName": "Section", "content": "Other"},
                    {"columnId": "1", "columnName": "Question", "content": "What do you know?"},
                    {
                        "columnId": "2",
                        "columnName": "Knowledge Base Answer",
                        "content": "Lorem Ipsum is simply dummy text.",
                    },
                ],
            },
        ],
        "ingestionConfiguration": {
            "columnIdsInMetadata": ["1", "2"],
            "columnIdsInChunkText": ["1", "2"],
        },
        "metadata": {
            "libraryName": "foo",
        },
        "scopeId": scope_id,
        "sheetName": "Sheet1",
    }

    unique_sdk.Content.ingest_magic_table_sheets(**params)
    ```

??? example "`unique_sdk.Content.update` - Update content"

    !!! info "Compatibility"
        Compatible with release >.36

    Update a file by its `contentId` or `filePath`.

    **Parameters:**

    - `contentId` (str, optional) - ID of the file to update (required if `filePath` not provided)
    - `filePath` (str, optional) - Absolute path of the file (required if `contentId` not provided)
    - `title` (str, optional) - New file title
    - `ownerId` (str, optional) - Move file to different folder using folder ID
    - `parentFolderPath` (str, optional) - Move file to different folder using folder path
    - `metadata` (Dict[str, str | None], optional) - Update file metadata (available in release >.40)

    **Returns:**

    Returns a [`ContentInfo`](#contentinfo) object.

    **Examples:**

    Update title by path:

    ```python
    unique_sdk.Content.update(
        user_id=user_id,
        company_id=company_id,
        filePath="/Company/finance/january.xls",
        title="Revision Deck"
    )
    ```

    Move file by content ID:

    ```python
    unique_sdk.Content.update(
        user_id=user_id,
        company_id=company_id,
        contentId="cont_ok2343q5owbce80w78hudawu5",
        ownerId="scope_e68yz5asho7glfh7c7d041el",
        metadata={
            "quarter": "q1",
        }
    )
    ```

    Move and update title:

    ```python
    unique_sdk.Content.update(
        user_id=user_id,
        company_id=company_id,
        contentId="cont_ok2343q5owbce80w78hudawu5",
        ownerId="scope_e68yz5asho7glfh7c7d041el",
        title="Revision Deck (1)"
    )
    ```

    Move by folder path:

    ```python
    unique_sdk.Content.update(
        user_id=user_id,
        company_id=company_id,
        contentId="cont_ok2343q5owbce80w78hudawu5",
        parentFolderPath="/Company/Revisions"
    )
    ```

??? example "`unique_sdk.Content.delete` - Delete content"

    !!! info "Compatibility"
        Compatible with release >.36

    Delete a file by its `contentId` or `filePath`.

    **Parameters:**

    - `contentId` (str, optional) - ID of the file to delete (required if `filePath` not provided)
    - `chatId` (str, optional) - Chat ID (required if file is part of a chat)
    - `filePath` (str, optional) - Absolute path of the file (required if `contentId` not provided)

    **Returns:**

    Returns a [`DeleteResponse`](#deleteresponse) object.

    **Examples:**

    Delete from chat:

    ```python
    unique_sdk.Content.delete(
        user_id=user_id,
        company_id=company_id,
        contentId="cont_ok2343q5owbce80w78hudawu5",
        chatId="chat_v3xfa7liv876h89vuiibus1"
    )
    ```

    Delete by path:

    ```python
    unique_sdk.Content.delete(
        user_id=user_id,
        company_id=company_id,
        filePath="/Company/finance/january.xls",
    )
    ```

## Use Cases

For simplified file operations, use the [File I/O utilities](../utilities/file_io.md):

??? example "Upload Files"

    Instead of manually handling the three-step `Content.upsert` process, use the `upload_file` utility:

    ```python
    from unique_sdk.utils.file_io import upload_file

    content = upload_file(
        userId=user_id,
        companyId=company_id,
        path_to_file="/path/to/document.pdf",
        displayed_filename="Q4_Report.pdf",
        mime_type="application/pdf",
        scope_or_unique_path="scope_abc123",
        ingestion_config={
            "chunkStrategy": "default",
            "chunkMaxTokens": 1000
        },
        metadata={
            "year": "2024",
            "department": "Finance"
        }
    )
    ```

??? example "Download Files"

    Use the `download_content` utility to download files from the knowledge base:

    ```python
    from unique_sdk.utils.file_io import download_content

    file_path = download_content(
        companyId=company_id,
        userId=user_id,
        content_id="cont_abc123",
        filename="report.pdf"
    )

    with open(file_path, "rb") as f:
        content = f.read()
    ```

??? example "Wait for Ingestion Completion"

    After uploading a file, wait for it to be fully ingested before using it:

    ```python
    from unique_sdk.utils.file_io import upload_file, wait_for_ingestion_completion
    import asyncio

    async def upload_and_wait(file_path, scope_id):
        content = upload_file(
            userId=user_id,
            companyId=company_id,
            path_to_file=file_path,
            displayed_filename="document.pdf",
            mime_type="application/pdf",
            scope_or_unique_path=scope_id
        )
        
        await wait_for_ingestion_completion(
            user_id=user_id,
            company_id=company_id,
            content_id=content.id
        )
        
        return content

    asyncio.run(upload_and_wait("/path/to/file.pdf", "scope_abc123"))
    ```

## Filtering

#### ContentWhereInput {#contentwhereinput}

??? note "The `ContentWhereInput` type defines filter conditions for searching content. It supports logical operators (`AND`, `OR`, `NOT`) and field-specific filters"

    **Available Fields:**

    - `id` - Filter by content ID (uses `StringFilter`)
    - `key` - Filter by file key/name (uses `StringFilter`)
    - `ownerId` - Filter by owner/folder ID (uses `StringFilter`)
    - `title` - Filter by content title (uses `StringNullableFilter`)
    - `url` - Filter by content URL (uses `StringNullableFilter`)

    **Logical Operators:**

    - `AND` - All conditions must match (array of `ContentWhereInput`)
    - `OR` - Any condition must match (array of `ContentWhereInput`)
    - `NOT` - Conditions must not match (array of `ContentWhereInput`)

    **String Filter Operators:**

    Each field filter supports the following operators:

    - `contains` (str) - Field contains the substring
    - `equals` (str) - Field equals the value exactly
    - `startsWith` (str) - Field starts with the value
    - `endsWith` (str) - Field ends with the value
    - `gt` (str) - Field is greater than the value
    - `gte` (str) - Field is greater than or equal to the value
    - `lt` (str) - Field is less than the value
    - `lte` (str) - Field is less than or equal to the value
    - `in_` (List[str]) - Field is in the list of values
    - `notIn` (List[str]) - Field is not in the list of values
    - `not_` (NestedStringFilter) - Negate a nested filter condition
    - `mode` (QueryMode) - Query mode: `"default"` or `"insensitive"` (case-insensitive)

    **Examples:**

    Simple filter:

    ```python
    where={
        "title": {
            "contains": "report"
        }
    }
    ```

    Multiple conditions with AND:

    ```python
    where={
        "AND": [
            {"title": {"contains": "report"}},
            {"ownerId": {"equals": "scope_abc123"}}
        ]
    }
    ```

    Multiple conditions with OR:

    ```python
    where={
        "OR": [
            {"title": {"contains": "report"}},
            {"key": {"contains": "report"}}
        ]
    }
    ```

    Case-insensitive search:

    ```python
    where={
        "title": {
            "contains": "Report",
            "mode": "insensitive"
        }
    }
    ```

    Using `in_` operator:

    ```python
    where={
        "id": {
            "in_": ["cont_123", "cont_456", "cont_789"]
        }
    }
    ```

    Complex nested conditions:

    ```python
    where={
        "AND": [
            {
                "OR": [
                    {"title": {"contains": "report"}},
                    {"title": {"contains": "summary"}}
                ]
            },
            {
                "NOT": [
                    {"ownerId": {"equals": "scope_excluded"}}
                ]
            }
        ]
    }
    ```

## Input Types

#### Content.Input {#contentinput}

??? note "The `Content.Input` type defines the structure for creating or updating content"

    **Fields:**

    - `key` (str, required) - File key/name
    - `title` (str, optional) - Content title
    - `mimeType` (str, required) - MIME type (e.g., "application/pdf", "text/plain")
    - `description` (str, optional) - Content description
    - `ownerType` (str, optional) - Owner type
    - `ownerId` (str, optional) - Owner/folder ID
    - `byteSize` (int, optional) - File size in bytes
    - `ingestionConfig` (IngestionConfig, optional) - Ingestion configuration
    - `metadata` (Dict[str, Any], optional) - Custom metadata dictionary

    **Used in:** `Content.upsert()`

## Return Types

#### Content {#content}

??? note "The `Content` object represents a full content item with chunks and URLs"

    **Fields:**

    - `id` (str) - Unique content identifier
    - `key` (str) - File key/name
    - `url` (str | None) - Content URL
    - `title` (str | None) - Content title
    - `updatedAt` (str) - Last update timestamp (ISO 8601)
    - `chunks` (List[Chunk] | None) - Document chunks with text and page information
    - `metadata` (Dict[str, Any] | None) - Custom metadata dictionary
    - `writeUrl` (str | None) - URL for uploading file content
    - `readUrl` (str | None) - URL for reading/downloading file content
    - `expiredAt` (str | None) - Expiration timestamp (ISO 8601)

    **Returned by:** `Content.search()`, `Content.upsert()`

#### Chunk {#chunk}

??? note "The `Chunk` object represents a text chunk within a document"

    **Fields:**

    - `id` (str) - Chunk identifier
    - `text` (str) - Chunk text content
    - `startPage` (int | None) - Starting page number
    - `endPage` (int | None) - Ending page number
    - `order` (int | None) - Chunk order in document

    **Used in:** `Content.chunks`

#### ContentInfo {#contentinfo}

??? note "The `ContentInfo` object represents basic information about a content item without full chunks."

    **Fields:**

    - `id` (str) - Unique content identifier
    - `key` (str) - File key/name
    - `url` (str | None) - Content URL
    - `title` (str | None) - Content title
    - `metadata` (Dict[str, Any] | None) - Custom metadata dictionary
    - `mimeType` (str) - MIME type of the file
    - `description` (str | None) - Content description
    - `byteSize` (int) - File size in bytes
    - `ownerId` (str) - Owner/folder ID
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)
    - `expiresAt` (str | None) - Expiration timestamp (ISO 8601)
    - `deletedAt` (str | None) - Deletion timestamp (ISO 8601)
    - `expiredAt` (str | None) - Expiration timestamp alias (ISO 8601)

    **Returned by:** `Content.get_info()`, `Content.get_infos()`, `Content.update()`

#### PaginatedContentInfo {#paginatedcontentinfo}

??? note "The `PaginatedContentInfo` object contains paginated content info results"

    **Fields:**

    - `contentInfo` (List[ContentInfo]) - List of content info objects
    - `totalCount` (int) - Total number of matching entries

    **Returned by:** `Content.get_info()`

#### PaginatedContentInfos {#paginatedcontentinfos}

??? note "The `PaginatedContentInfos` object contains paginated content infos results"

    **Fields:**

    - `contentInfos` (List[ContentInfo]) - List of content info objects
    - `totalCount` (int) - Total number of matching entries

    **Returned by:** `Content.get_infos()`

#### MagicTableSheetResponse {#magictablesheetresponse}

??? note "The `MagicTableSheetResponse` object contains the mapping of row IDs to created content IDs"

    **Fields:**

    - `rowIdsToContentIds` (List[MagicTableSheetRowIdToContentId]) - Mapping of row IDs to created content IDs

    **MagicTableSheetRowIdToContentId Fields:**

    - `rowId` (str) - Original row identifier
    - `contentId` (str) - Created content identifier

    **Returned by:** `Content.ingest_magic_table_sheets()`

#### DeleteResponse {#deleteresponse}

??? note "The `DeleteResponse` object contains the ID of deleted content"

    **Fields:**

    - `id` (str) - ID of the deleted content

    **Returned by:** `Content.delete()`

## Related Resources

- [File I/O Utilities](../utilities/file_io.md) - Simplified file upload and download
- [Folder API](folder.md) - Organize content into folders
- [Search API](search.md) - Search across content
- [UniqueQL](../uniqueql.md) - Query language for filtering

