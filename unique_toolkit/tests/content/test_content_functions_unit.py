from unittest.mock import Mock, patch

import pytest

from unique_toolkit.content.functions import (
    download_content,
    download_content_to_bytes,
    download_content_to_file_by_id,
    request_content_by_id,
    search_content_chunks,
    search_content_chunks_async,
    search_contents,
    search_contents_async,
    upload_content,
    upload_content_from_bytes,
)
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentRerankerConfig,
    ContentSearchType,
)


@patch("unique_toolkit.content.functions.unique_sdk")
def test_search_content_chunks(mock_sdk, base_content_chunk):
    # Setup
    mock_sdk.Search.create.return_value = [base_content_chunk.model_dump()]

    # Execute
    result = search_content_chunks(
        user_id="user123",
        company_id="company123",
        chat_id="chat123",
        search_string="test query",
        search_type=ContentSearchType.VECTOR,
        limit=10,
        scope_ids=["scope123"],
    )

    # Assert
    assert isinstance(result, list)
    assert all(isinstance(chunk, ContentChunk) for chunk in result)
    mock_sdk.Search.create.assert_called_once()
    assert len(result) == 1
    assert result[0].text == "Test chunk content"


@pytest.mark.asyncio
@patch("unique_toolkit.content.functions.unique_sdk")
async def test_search_content_chunks_async(mock_sdk, base_content_chunk):
    # Setup
    async def async_return():
        return [base_content_chunk.model_dump()]

    mock_sdk.Search.create_async.return_value = async_return()

    # Execute
    result = await search_content_chunks_async(
        user_id="user123",
        company_id="company123",
        chat_id="chat123",
        search_string="test query",
        search_type=ContentSearchType.VECTOR,
        limit=10,
        scope_ids=["scope123"],
    )

    # Assert
    assert isinstance(result, list)
    assert all(isinstance(chunk, ContentChunk) for chunk in result)
    mock_sdk.Search.create_async.assert_called_once()


@patch("unique_toolkit.content.functions.unique_sdk")
def test_search_contents(mock_sdk):
    # Setup
    content_data = {
        "id": "content_123",
        "key": "test_key",
        "title": "Test Document",
        "url": None,
        "chunks": [],
        "createdAt": "2021-01-01T00:00:00Z",
        "updatedAt": "2021-01-01T00:00:00Z",
    }
    mock_sdk.Content.search.return_value = [content_data]

    # Execute
    result = search_contents(
        user_id="user123",
        company_id="company123",
        chat_id="chat123",
        where={"key": "test.pdf"},
    )

    # Assert
    assert isinstance(result, list)
    assert all(isinstance(content, Content) for content in result)
    mock_sdk.Content.search.assert_called_once()


@pytest.mark.asyncio
@patch("unique_toolkit.content.functions.unique_sdk")
async def test_search_contents_async(mock_sdk):
    # Setup
    content_data = {
        "id": "content_123",
        "key": "test_key",
        "title": "Test Document",
        "url": None,
        "chunks": [],
        "createdAt": "2021-01-01T00:00:00Z",
        "updatedAt": "2021-01-01T00:00:00Z",
    }

    async def async_return():
        return [content_data]

    mock_sdk.Content.search_async.return_value = async_return()

    # Execute
    result = await search_contents_async(
        user_id="user123",
        company_id="company123",
        chat_id="chat123",
        where={"key": "test.pdf"},
    )

    # Assert
    assert isinstance(result, list)
    assert all(isinstance(content, Content) for content in result)
    mock_sdk.Content.search_async.assert_called_once()


@patch("unique_toolkit.content.functions.requests.put")
@patch("unique_toolkit.content.functions._upsert_content")
def test_upload_content(mock_upsert, mock_put, tmp_path):
    # Setup
    content_data = {
        "id": "content_123",
        "key": "test_key",
        "title": "Test Document",
        "writeUrl": "http://test-write-url.com",
        "readUrl": "http://test-read-url.com",
    }
    mock_upsert.return_value = content_data
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    ingestion_config = {
        "chunkStrategy": "default",
        "uniqueIngestionMode": "standard",
    }

    # Execute
    result = upload_content(
        user_id="user123",
        company_id="company123",
        path_to_content=str(test_file),
        content_name="test.txt",
        mime_type="text/plain",
        scope_id="scope123",
        ingestion_config=ingestion_config,
    )

    # Assert
    assert isinstance(result, Content)
    mock_upsert.assert_called()
    mock_put.assert_called_once()
    call_kwargs = mock_upsert.call_args[1]
    assert call_kwargs["input_data"]["ingestionConfig"] == ingestion_config


@patch("unique_toolkit.content.functions.requests.put")
@patch("unique_toolkit.content.functions._upsert_content")
def test_upload_content_from_bytes(mock_upsert, mock_put):
    # Setup
    content_data = {
        "id": "content_123",
        "key": "test_key",
        "title": "Test Document",
        "writeUrl": "http://test-write-url.com",
        "readUrl": "http://test-read-url.com",
    }
    mock_upsert.return_value = content_data
    content = b"test content"

    ingestion_config = {
        "chunkStrategy": "default",
        "uniqueIngestionMode": "standard",
    }

    # Execute
    result = upload_content_from_bytes(
        user_id="user123",
        company_id="company123",
        content=content,
        content_name="test.txt",
        mime_type="text/plain",
        scope_id="scope123",
        ingestion_config=ingestion_config,
    )

    # Assert
    assert isinstance(result, Content)
    call_kwargs = mock_upsert.call_args[1]
    assert call_kwargs["input_data"]["ingestionConfig"] == ingestion_config


@patch("unique_toolkit.content.functions.requests.get")
def test_download_content_to_file_by_id(mock_get, tmp_path):
    # Setup
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test content"
    mock_response.headers = {"Content-Disposition": 'filename="test.txt"'}
    mock_get.return_value = mock_response

    # Execute
    result = download_content_to_file_by_id(
        user_id="user123",
        company_id="company123",
        content_id="content123",
        chat_id="chat123",
        tmp_dir_path=tmp_path,
    )

    # Assert
    assert result.exists()
    assert result.read_text() == "test content"
    mock_get.assert_called_once()


@patch("unique_toolkit.content.functions.unique_sdk")
def test_download_content(mock_sdk, tmp_path):
    # Setup
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test content"

    with patch(
        "unique_toolkit.content.functions.request_content_by_id",
        return_value=mock_response,
    ):
        # Execute
        result = download_content(
            user_id="user123",
            company_id="company123",
            content_id="content123",
            content_name="test.txt",
            chat_id="chat123",
            dir_path=tmp_path,
        )

        # Assert
        assert result.exists()
        assert result.read_text() == "test content"


@patch("unique_toolkit.content.functions.request_content_by_id")
def test_download_content_to_memory(mock_request):
    # Setup
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test content"

    mock_request.return_value = mock_response

    # Execute
    result = download_content_to_bytes(
        user_id="user123",
        company_id="company123",
        content_id="content123",
        chat_id="chat123",
    )

    # Assert
    assert result == b"test content"


@patch("unique_toolkit.content.functions.unique_sdk")
def test_search_with_reranker_config(mock_sdk, base_content_chunk):
    # Setup
    mock_sdk.Search.create.return_value = [base_content_chunk.model_dump()]
    reranker_config = ContentRerankerConfig(
        deployment_name="test-deployment",
        options={"model": "test-model", "temperature": 0.7},
    )

    # Execute
    result = search_content_chunks(
        user_id="user123",
        company_id="company123",
        chat_id="chat123",
        search_string="test query",
        search_type=ContentSearchType.VECTOR,
        limit=10,
        reranker_config=reranker_config,
    )

    # Assert
    assert isinstance(result, list)
    mock_sdk.Search.create.assert_called_once()
    call_kwargs = mock_sdk.Search.create.call_args[1]
    assert "reranker" in call_kwargs
    assert call_kwargs["reranker"]["deploymentName"] == "test-deployment"


@patch("unique_toolkit.content.functions.unique_sdk")
def test_search_with_metadata_filter(mock_sdk, base_content_chunk):
    # Setup
    mock_sdk.Search.create.return_value = [base_content_chunk.model_dump()]
    metadata_filter = {"category": "test"}

    # Execute
    result = search_content_chunks(
        user_id="user123",
        company_id="company123",
        chat_id="chat123",
        search_string="test query",
        search_type=ContentSearchType.VECTOR,
        limit=10,
        metadata_filter=metadata_filter,
    )

    # Assert
    assert isinstance(result, list)
    mock_sdk.Search.create.assert_called_once()
    call_kwargs = mock_sdk.Search.create.call_args[1]
    assert call_kwargs["metaDataFilter"] == metadata_filter


@patch("unique_toolkit.content.functions.unique_sdk")
def test_upload_content_error_handling(mock_sdk, tmp_path):
    # Setup
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Test missing required parameters
    with pytest.raises(ValueError):
        upload_content(
            user_id="user123",
            company_id="company123",
            path_to_content=str(test_file),
            content_name="test.txt",
            mime_type="text/plain",
            # Both scope_id and chat_id missing
        )


@patch("unique_toolkit.content.functions.requests.put")
@patch("unique_toolkit.content.functions._upsert_content")
def test_upload_content_with_metadata(mock_upsert, mock_put, tmp_path):
    # Setup
    content_data = {
        "id": "content_123",
        "key": "test_key",
        "title": "Test Document",
        "url": None,
        "chunks": [],
        "createdAt": "2021-01-01T00:00:00Z",
        "updatedAt": "2021-01-01T00:00:00Z",
        "writeUrl": "https://example.com/write",
        "readUrl": "https://example.com/read",
    }
    mock_upsert.return_value = content_data
    content = b"test content"

    metadata = {
        "key": "value",
    }

    # Execute
    result = upload_content_from_bytes(
        user_id="user123",
        company_id="company123",
        content=content,
        content_name="test.txt",
        mime_type="text/plain",
        scope_id="scope123",
        metadata=metadata,
    )

    # Assert
    assert isinstance(result, Content)
    call_kwargs = mock_upsert.call_args[1]
    assert call_kwargs["input_data"]["metadata"] == metadata


@patch("unique_toolkit.content.functions.unique_sdk")
def test_request_content_by_id(mock_sdk):
    # Setup
    with patch("unique_toolkit.content.functions.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_get.return_value = mock_response

        # Execute
        response = request_content_by_id(
            user_id="user123",
            company_id="company123",
            content_id="content123",
            chat_id="chat123",
        )

        # Assert
        assert response.status_code == 200
        assert response.content == b"test content"
        mock_get.assert_called_once()
        # Verify headers
        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        headers = call_kwargs["headers"]
        assert headers["x-user-id"] == "user123"
        assert headers["x-company-id"] == "company123"


@patch("unique_toolkit.content.functions.unique_sdk")
def test_download_content_to_file_by_id_error(mock_sdk):
    # Setup
    with patch(
        "unique_toolkit.content.functions.request_content_by_id"
    ) as mock_request:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            download_content_to_file_by_id(
                user_id="user123",
                company_id="company123",
                content_id="content123",
                chat_id="chat123",
            )
        assert "Error downloading file: Status code 404" in str(exc_info.value)


@patch("unique_toolkit.content.functions.unique_sdk")
def test_download_content_to_file_by_id_no_filename(mock_sdk):
    # Setup
    with patch(
        "unique_toolkit.content.functions.request_content_by_id"
    ) as mock_request:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_response.headers = {}  # No Content-Disposition header
        mock_request.return_value = mock_response

        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            download_content_to_file_by_id(
                user_id="user123", company_id="company123", content_id="content123"
            )
        assert "Filename could not be determined" in str(exc_info.value)


@patch("unique_toolkit.content.functions.unique_sdk")
def test_search_content_chunks_sdk_error(mock_sdk):
    # Setup
    mock_sdk.Search.create.side_effect = Exception("SDK error")

    # Execute & Assert
    with pytest.raises(Exception) as exc_info:
        search_content_chunks(
            user_id="user123",
            company_id="company123",
            chat_id="chat123",
            search_string="test query",
            search_type=ContentSearchType.VECTOR,
            limit=10,
        )
    assert isinstance(exc_info.value, Exception)
    assert str(exc_info.value) == "SDK error"


@pytest.mark.asyncio
@patch("unique_toolkit.content.functions.unique_sdk")
async def test_search_contents_async_error(mock_sdk):
    # Setup
    mock_sdk.Content.search_async.side_effect = Exception("SDK error")

    # Execute & Assert
    with pytest.raises(Exception) as exc_info:
        await search_contents_async(
            user_id="user123",
            company_id="company123",
            chat_id="chat123",
            where={"key": "test.pdf"},
        )
    assert isinstance(exc_info.value, Exception)
    assert str(exc_info.value) == "SDK error"


@patch("unique_toolkit.content.functions.unique_sdk")
def test_upload_content_missing_write_url(mock_sdk, tmp_path):
    # Setup
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    mock_sdk.Content.upsert.return_value = {
        "id": "content123",
        "writeUrl": None,
        "readUrl": "http://example.com/read",
        "key": "test.txt",
        "title": "Test Document",
        "mimeType": "text/plain",
        "url": "http://example.com/content",
        "chunks": [],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }

    ingestion_config = {
        "chunkMaxTokens": 1000,
        "chunkStrategy": "default",
        "uniqueIngestionMode": "standard",
    }

    # Execute & Assert
    with pytest.raises(ValueError) as exc_info:
        upload_content(
            user_id="user123",
            company_id="company123",
            path_to_content=str(test_file),
            content_name="test.txt",
            mime_type="text/plain",
            scope_id="scope123",
            ingestion_config=ingestion_config,
        )
    assert "Write url for uploaded content is missing" in str(exc_info.value)
