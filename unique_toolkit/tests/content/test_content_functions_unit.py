from unittest.mock import AsyncMock, Mock, patch

import pytest

from unique_toolkit.content.functions import (
    _extract_filename,
    download_content,
    download_content_to_bytes,
    download_content_to_bytes_async,
    download_content_to_file_by_id,
    request_content_by_id,
    request_content_by_id_async,
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


@pytest.fixture
def mock_sdk():
    with patch("unique_toolkit.content.functions.unique_sdk") as mock:
        yield mock


@pytest.fixture
def sample_content_chunk_data():
    return {
        "id": "chunk123",
        "text": "Test content chunk",
        "content": "Test content chunk",
        "order": 1,
        "metadata": {"page": 1, "key": "test.pdf", "mimeType": "application/pdf"},
        "score": 0.95,
    }


@pytest.fixture
def sample_content_data():
    return {
        "id": "content123",
        "key": "test.pdf",
        "title": "Test Document",
        "mimeType": "application/pdf",
        "readUrl": "http://example.com/read",
        "writeUrl": "http://example.com/write",
        "url": "http://example.com/content",
        "chunks": [],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "ingestionState": "FINISHED",
    }


def test_search_content_chunks(mock_sdk, sample_content_chunk_data):
    # Setup
    mock_sdk.Search.create.return_value = [sample_content_chunk_data]

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
    assert result[0].text == "Test content chunk"


@pytest.mark.asyncio
async def test_search_content_chunks_async(mock_sdk, sample_content_chunk_data):
    # Setup
    async def async_return():
        return [sample_content_chunk_data]

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


def test_search_contents(mock_sdk, sample_content_data):
    # Setup
    mock_sdk.Content.search.return_value = [sample_content_data]

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
async def test_search_contents_async(mock_sdk, sample_content_data):
    # Setup
    async def async_return():
        return [sample_content_data]

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
def test_upload_content(mock_upsert, mock_put, mock_sdk, sample_content_data, tmp_path):
    # Setup
    mock_upsert.return_value = sample_content_data
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
def test_upload_content_from_bytes(mock_upsert, mock_put, sample_content_data):
    # Setup
    mock_upsert.return_value = sample_content_data
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


@patch("unique_toolkit.content.functions.requests.put")
@patch("unique_toolkit.content.functions._upsert_content")
def test_upload_content_from_bytes_uses_ingestion_upload_url_internal_when_set(
    mock_upsert, mock_put, sample_content_data
):
    mock_upsert.return_value = sample_content_data
    internal_base = "https://node-ingestion.internal/upload"
    with patch(
        "unique_toolkit.content.utils._ingestion_upload_api_url_internal",
        internal_base,
    ):
        result = upload_content_from_bytes(
            user_id="user123",
            company_id="company123",
            content=b"test",
            content_name="test.txt",
            mime_type="text/plain",
            scope_id="scope123",
        )
    assert result.write_url is not None
    assert result.write_url.startswith(internal_base)
    mock_put.assert_called_once()
    assert mock_put.call_args[1]["url"].startswith(internal_base)


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


def test_search_with_reranker_config(mock_sdk, sample_content_chunk_data):
    # Setup
    mock_sdk.Search.create.return_value = [sample_content_chunk_data]
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


def test_search_with_metadata_filter(mock_sdk, sample_content_chunk_data):
    # Setup
    mock_sdk.Search.create.return_value = [sample_content_chunk_data]
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
def test_upload_content_with_metadata(
    mock_upsert, mock_put, mock_sdk, sample_content_data, tmp_path
):
    # Setup
    mock_upsert.return_value = sample_content_data
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


@pytest.mark.ai
@pytest.mark.asyncio
async def test_request_content_by_id_async__returns_response__with_valid_params(
    mock_sdk,
) -> None:
    """
    Purpose: Verify async content request builds correct URL with chat_id and auth headers.
    Why this matters: Incorrect URL or headers would silently fail content downloads.
    Setup summary: Mock httpx.AsyncClient, call request_content_by_id_async, assert URL and headers.
    """
    with patch("unique_toolkit.content.functions.httpx.AsyncClient") as mock_client_cls:
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        # Act
        response = await request_content_by_id_async(
            user_id="user123",
            company_id="company123",
            content_id="content123",
            chat_id="chat123",
        )

        # Assert
        assert response.status_code == 200
        assert response.content == b"test content"
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "content123" in call_args[0][0]
        assert "chatId=chat123" in call_args[0][0]
        headers = call_args[1]["headers"]
        assert headers["x-user-id"] == "user123"
        assert headers["x-company-id"] == "company123"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_download_content_to_bytes_async__returns_bytes__with_successful_response(
    mock_sdk,
) -> None:
    """
    Purpose: Verify async download returns raw bytes when the response is successful.
    Why this matters: Callers depend on receiving bytes for in-memory file processing.
    Setup summary: Mock request_content_by_id_async with a 200 response, assert bytes returned.
    """
    # Arrange
    mock_response = Mock()
    mock_response.is_success = True
    mock_response.content = b"test content"

    async def fake_request(*args):
        return mock_response

    with patch(
        "unique_toolkit.content.functions.request_content_by_id_async",
        side_effect=fake_request,
    ):
        # Act
        result = await download_content_to_bytes_async(
            user_id="user123",
            company_id="company123",
            content_id="content123",
            chat_id="chat123",
        )

        # Assert
        assert isinstance(result, bytes)
        assert result == b"test content"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_download_content_to_bytes_async__raises_error__when_response_not_successful(
    mock_sdk,
) -> None:
    """
    Purpose: Verify async download raises when the server returns a non-success status.
    Why this matters: Silent failures on bad responses would produce corrupt or missing data.
    Setup summary: Mock request with is_success=False and raise_for_status side effect, assert raises.
    """
    # Arrange
    mock_response = Mock()
    mock_response.is_success = False
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = RuntimeError("download failed")

    async def fake_request(*args):
        return mock_response

    with patch(
        "unique_toolkit.content.functions.request_content_by_id_async",
        side_effect=fake_request,
    ):
        # Act & Assert
        with pytest.raises(RuntimeError, match="download failed"):
            await download_content_to_bytes_async(
                user_id="user123",
                company_id="company123",
                content_id="content123",
                chat_id="chat123",
            )


# ---------------------------------------------------------------------------
# httpx timeout tests for _trigger_upload_content_async (UN-18453)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_upload_content_async_uses_generous_timeout(
    sample_content_data,
) -> None:
    """
    Purpose: Verify AsyncClient is created with read/write timeouts well above the 5 s default.
    Why this matters: Large HTML files (~4 MB) reliably timeout at 5 s waiting for the Azure
    Blob Storage commit response; without an explicit timeout the upload silently fails.
    Setup summary: Patch _upsert_content_async and httpx.AsyncClient, call the private helper,
    assert the timeout kwarg has read >= 60 and write >= 60.
    """
    import httpx

    from unique_toolkit.content.functions import _trigger_upload_content_async

    captured_timeout: httpx.Timeout | None = None

    with patch(
        "unique_toolkit.content.functions._upsert_content_async",
        new_callable=AsyncMock,
    ) as mock_upsert:
        mock_upsert.return_value = sample_content_data

        with patch(
            "unique_toolkit.content.functions.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.put.return_value = mock_response
            mock_client_cls.return_value = mock_client

            def capture_timeout(*args, **kwargs):
                nonlocal captured_timeout
                captured_timeout = kwargs.get("timeout")
                return mock_client

            mock_client_cls.side_effect = capture_timeout

            await _trigger_upload_content_async(
                user_id="user123",
                company_id="company123",
                content=b"<html>large payload</html>",
                content_name="dashboard.html",
                mime_type="text/html",
                chat_id="chat123",
            )

    assert captured_timeout is not None, (
        "httpx.AsyncClient must receive a timeout= kwarg"
    )
    assert isinstance(captured_timeout, httpx.Timeout)
    assert captured_timeout.read is not None and captured_timeout.read >= 60, (
        f"read timeout {captured_timeout.read} must be >= 60 s to survive large blob uploads"
    )
    assert captured_timeout.write is not None and captured_timeout.write >= 60, (
        f"write timeout {captured_timeout.write} must be >= 60 s to survive large blob uploads"
    )


@pytest.mark.asyncio
async def test_trigger_upload_content_async_timeout_not_default_5s(
    sample_content_data,
) -> None:
    """
    Purpose: Guard against accidental regression back to the 5 s httpx default.
    Why this matters: A plain httpx.AsyncClient() has read=write=5 s which causes ReadTimeout
    for ~4 MB HTML artifacts (observed in production, chat chat_n2ww1gbf0bti31gh8dt95hox).
    """
    import httpx

    from unique_toolkit.content.functions import _trigger_upload_content_async

    with patch(
        "unique_toolkit.content.functions._upsert_content_async",
        new_callable=AsyncMock,
    ) as mock_upsert:
        mock_upsert.return_value = sample_content_data

        with patch(
            "unique_toolkit.content.functions.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.put.return_value = mock_response
            mock_client_cls.return_value = mock_client

            await _trigger_upload_content_async(
                user_id="user123",
                company_id="company123",
                content=b"<html>large payload</html>",
                content_name="dashboard.html",
                mime_type="text/html",
                chat_id="chat123",
            )

            call_kwargs = mock_client_cls.call_args[1]
            timeout = call_kwargs.get("timeout")

    assert timeout is not None, (
        "timeout= must be passed explicitly to httpx.AsyncClient"
    )
    assert not isinstance(timeout, httpx.Timeout) or timeout.read != 5.0, (
        "read timeout must not be the default 5 s"
    )


class TestExtractFilename:
    def test_prefers_utf8_filename_over_ascii(self):
        header = (
            'attachment; filename="??? ???????.pptx"; '
            "filename*=UTF-8''%D0%98%D0%9A%D0%A2%20%D0%A3%D0%A0%D0%95%D0%82%D0%90%D0%88%D0%98.pptx"
        )
        assert _extract_filename(header) == "ИКТ УРЕЂАЈИ.pptx"

    def test_utf8_filename_only(self):
        header = "attachment; filename*=UTF-8''%C3%BCbersicht.pdf"
        assert _extract_filename(header) == "übersicht.pdf"

    def test_falls_back_to_ascii_filename(self):
        header = 'attachment; filename="report.pdf"'
        assert _extract_filename(header) == "report.pdf"

    def test_returns_none_when_no_filename(self):
        assert _extract_filename("") is None
        assert _extract_filename("attachment") is None

    def test_case_insensitive_charset(self):
        header = "attachment; filename*=utf-8''%C3%A9t%C3%A9.docx"
        assert _extract_filename(header) == "été.docx"

    def test_latin_diacritics(self):
        header = "attachment; filename=\"obican.txt\"; filename*=UTF-8''obi%C4%8Dan.txt"
        assert _extract_filename(header) == "običan.txt"

    def test_with_language_tag(self):
        header = "attachment; filename*=UTF-8'sr'%D0%98%D0%9A%D0%A2%20%D0%A3%D0%A0%D0%95%D0%82%D0%90%D0%88%D0%98.pptx"
        assert _extract_filename(header) == "ИКТ УРЕЂАЈИ.pptx"

    def test_with_language_tag_and_ascii_fallback(self):
        header = "attachment; filename=\"fallback.pptx\"; filename*=UTF-8'en'%C3%BCbersicht.pdf"
        assert _extract_filename(header) == "übersicht.pdf"


@patch("unique_toolkit.content.functions.requests.get")
def test_download_content_to_file_by_id_utf8_filename(mock_get, tmp_path):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"file bytes"
    mock_response.headers = {
        "Content-Disposition": (
            'attachment; filename="??? ???????.pptx"; '
            "filename*=UTF-8''%D0%98%D0%9A%D0%A2%20%D0%A3%D0%A0%D0%95%D0%82%D0%90%D0%88%D0%98.pptx"
        )
    }
    mock_get.return_value = mock_response

    result = download_content_to_file_by_id(
        user_id="user123",
        company_id="company123",
        content_id="content123",
        chat_id="chat123",
        tmp_dir_path=tmp_path,
    )

    assert result.exists()
    assert result.name == "ИКТ УРЕЂАЈИ.pptx"
    assert result.read_bytes() == b"file bytes"
