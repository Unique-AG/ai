# File I/O Utility

Helper functions for uploading and downloading files to/from the Unique AI knowledge base.

## Overview

The File I/O utilities simplify:

- Uploading files to scopes or chats
- Downloading files from the knowledge base
- Waiting for ingestion completion
- Managing file ingestion
- Handling file metadata and configurations

## Methods

??? example "`unique_sdk.utils.file_io.upload_file` - Upload files to knowledge base"

    Upload a file to a scope or chat. The file will be automatically ingested into the knowledge base.

    **Parameters:**

    - `userId` (required) - User ID
    - `companyId` (required) - Company ID
    - `path_to_file` (required) - Local file path to upload
    - `displayed_filename` (required) - Name to display in the UI
    - `mime_type` (required) - MIME type (e.g., `"application/pdf"`, `"text/plain"`)
    - `description` (optional) - File description
    - `scope_or_unique_path` (optional) - Scope ID or unique path (required if `chat_id` not provided)
    - `chat_id` (optional) - Chat ID to upload to (required if `scope_or_unique_path` not provided)
    - `ingestion_config` (optional) - Ingestion configuration
    - `metadata` (optional) - Custom metadata dictionary

    **Returns:**

    - `Content` object with file details

    **Example - Upload to Scope:**

    ```python
    from unique_sdk.utils.file_io import upload_file

    content = upload_file(
        userId=user_id,
        companyId=company_id,
        path_to_file="/path/to/document.pdf",
        displayed_filename="Q4_Report_2024.pdf",
        mime_type="application/pdf",
        description="Quarterly financial report",
        scope_or_unique_path="scope_stcj2osgbl722m22jayidx0n",
        ingestion_config={
            "chunkStrategy": "default",
            "chunkMaxTokens": 1000
        },
        metadata={
            "year": "2024",
            "quarter": "Q4",
            "department": "Finance"
        }
    )

    print(f"Uploaded: {content.id}")
    print(f"Read URL: {content.readUrl}")
    ```

    **Example - Upload to Chat:**

    ```python
    content = upload_file(
        userId=user_id,
        companyId=company_id,
        path_to_file="/tmp/analysis.xlsx",
        displayed_filename="Data Analysis.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        chat_id="chat_abc123"
    )
    ```

??? example "`unique_sdk.utils.file_io.download_content` - Download files from knowledge base"

    Download a file from the knowledge base and save it to a temporary directory.

    **Parameters:**

    - `companyId` (required) - Company ID
    - `userId` (required) - User ID
    - `content_id` (required) - Content ID to download
    - `filename` (required) - Filename to save as
    - `chat_id` (optional) - Chat ID if file is in a chat

    **Returns:**

    - `Path` object pointing to the downloaded file in `/tmp`

    **Example:**

    ```python
    from unique_sdk.utils.file_io import download_content

    # Download from scope
    file_path = download_content(
        companyId=company_id,
        userId=user_id,
        content_id="cont_abc123",
        filename="report.pdf"
    )

    print(f"Downloaded to: {file_path}")
    # Use the file
    with open(file_path, "rb") as f:
        content = f.read()
    ```

    **Example - Download from Chat:**

    ```python
    file_path = download_content(
        companyId=company_id,
        userId=user_id,
        content_id="cont_xyz789",
        filename="document.pdf",
        chat_id="chat_abc123"
    )
    ```

??? example "`unique_sdk.utils.file_io.wait_for_ingestion_completion` - Wait for file ingestion"

    Polls until content ingestion is finished or the maximum wait time is reached. Raises an error if ingestion fails.

    **Parameters:**

    - `user_id` (required) - User ID
    - `company_id` (required) - Company ID
    - `content_id` (required) - Content ID to monitor
    - `chat_id` (optional) - Chat ID if content is in a chat
    - `poll_interval` (optional) - Seconds between polls (default: 1.0)
    - `max_wait` (optional) - Maximum seconds to wait (default: 60.0)

    **Returns:**

    - `"FINISHED"` when ingestion completes successfully

    **Raises:**

    - `RuntimeError` - If ingestion fails
    - `TimeoutError` - If max wait time is exceeded

    **Example:**

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
            content_id=content.id,
            poll_interval=2.0,
            max_wait=120.0
        )
        
        print(f"File {content.id} ingested successfully!")
        return content

    # Usage
    asyncio.run(upload_and_wait("/path/to/file.pdf", "scope_abc123"))
    ```

## Use Cases

??? example "Bulk File Upload"

    ```python
    from unique_sdk.utils.file_io import upload_file
    import os

    def upload_directory(directory_path, scope_id):
        """Upload all files in a directory."""
        uploaded = []
        
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            
            if os.path.isfile(file_path):
                # Determine MIME type
                if filename.endswith('.pdf'):
                    mime_type = "application/pdf"
                elif filename.endswith('.docx'):
                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                else:
                    mime_type = "application/octet-stream"
                
                try:
                    content = upload_file(
                        userId=user_id,
                        companyId=company_id,
                        path_to_file=file_path,
                        displayed_filename=filename,
                        mime_type=mime_type,
                        scope_or_unique_path=scope_id
                    )
                    uploaded.append(content.id)
                    print(f"✓ Uploaded: {filename}")
                except Exception as e:
                    print(f"✗ Failed: {filename} - {e}")
        
        return uploaded

    # Usage
    uploaded_ids = upload_directory("/path/to/documents", "scope_abc123")
    ```

??? example "Process Downloaded Files"

    ```python
    from unique_sdk.utils.file_io import download_content
    import tempfile

    def process_content_file(content_id):
        """Download and process a content file."""
        # Download to temp directory
        file_path = download_content(
            companyId=company_id,
            userId=user_id,
            content_id=content_id,
            filename="temp_file.pdf"
        )
        
        try:
            # Process the file
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            # Do something with the file
            process_file(file_data)
            
        finally:
            # Clean up temp file
            if file_path.exists():
                file_path.unlink()
    ```

## Best Practices

??? example "Set Appropriate Ingestion Config"

    ```python
    # For technical documents - larger chunks
    upload_file(
        ...,
        ingestion_config={
            "chunkStrategy": "default",
            "chunkMaxTokens": 2000  # Larger chunks
        }
    )

    # For short documents - smaller chunks
    upload_file(
        ...,
        ingestion_config={
            "chunkStrategy": "default",
            "chunkMaxTokens": 500  # Smaller chunks
        }
    )
    ```

??? example "Add Metadata for Better Searchability"

    ```python
    upload_file(
        ...,
        metadata={
            "year": "2024",
            "quarter": "Q1",
            "department": "Engineering",
            "document_type": "report",
            "author": "John Doe",
            "tags": ["technical", "architecture"]
        }
    )
    ```

## Related Resources

- [Content API](../api_resources/content.md) - Manage content in knowledge base
- [Folder API](../api_resources/folder.md) - Organize files in folders
- [Search API](../api_resources/search.md) - Search uploaded files

