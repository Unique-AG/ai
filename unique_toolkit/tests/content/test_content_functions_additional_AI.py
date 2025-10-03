"""
Additional tests for content functions to improve coverage.
These tests focus on edge cases, error handling, and uncovered code paths.
"""

from unittest.mock import patch

import pytest

from unique_toolkit.content.functions import (
    _trigger_upload_content,
    download_content,
    download_content_to_bytes,
    download_content_to_file_by_id,
    search_content_chunks,
    search_content_chunks_async,
    search_contents,
    search_contents_async,
    upload_content,
    upload_content_from_bytes,
)
from unique_toolkit.content.schemas import (
    Content,
    ContentSearchType,
)


@pytest.mark.ai
class TestContentFunctionsAdditional:
    """Additional tests for content functions to improve coverage."""

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_search_content_chunks__with_content_ids_logging_AI(self, mock_sdk):
        """
        Purpose: Verify that content_ids parameter triggers appropriate logging.
        Why this matters: Ensures proper logging for debugging content-specific searches.
        Setup summary: Mock SDK and provide content_ids parameter.
        """
        # Arrange
        mock_sdk.Search.create.return_value = []
        content_ids = ["content1", "content2"]

        # Act
        with patch("unique_toolkit.content.functions.logger") as mock_logger:
            search_content_chunks(
                user_id="user123",
                company_id="company123",
                chat_id="chat123",
                search_string="test query",
                search_type=ContentSearchType.VECTOR,
                limit=10,
                content_ids=content_ids,
            )

        # Assert
        mock_logger.info.assert_called_once()
        assert "content_ids" in str(mock_logger.info.call_args)

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_search_content_chunks__with_no_scope_ids_warning_AI(self, mock_sdk):
        """
        Purpose: Verify warning is logged when no scope_ids are provided.
        Why this matters: Helps developers identify potential search issues.
        Setup summary: Mock SDK and call without scope_ids.
        """
        # Arrange
        mock_sdk.Search.create.return_value = []

        # Act
        with patch("unique_toolkit.content.functions.logger") as mock_logger:
            search_content_chunks(
                user_id="user123",
                company_id="company123",
                chat_id="chat123",
                search_string="test query",
                search_type=ContentSearchType.VECTOR,
                limit=10,
                scope_ids=None,
            )

        # Assert
        mock_logger.warning.assert_called_once()
        assert "No scope IDs provided" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    @patch("unique_toolkit.content.functions.unique_sdk")
    async def test_search_content_chunks_async__with_content_ids_logging_AI(
        self, mock_sdk
    ):
        """
        Purpose: Verify async search logs content_ids parameter.
        Why this matters: Ensures consistent logging between sync and async methods.
        Setup summary: Mock SDK and provide content_ids for async search.
        """

        # Arrange
        async def async_return():
            return []

        mock_sdk.Search.create_async.return_value = async_return()
        content_ids = ["content1", "content2"]

        # Act
        with patch("unique_toolkit.content.functions.logger") as mock_logger:
            await search_content_chunks_async(
                user_id="user123",
                company_id="company123",
                chat_id="chat123",
                search_string="test query",
                search_type=ContentSearchType.VECTOR,
                limit=10,
                content_ids=content_ids,
            )

        # Assert
        mock_logger.info.assert_called_once()
        assert "asynchronously" in str(mock_logger.info.call_args)

    @pytest.mark.asyncio
    @patch("unique_toolkit.content.functions.unique_sdk")
    async def test_search_content_chunks_async__with_no_scope_ids_warning_AI(
        self, mock_sdk
    ):
        """
        Purpose: Verify async search warns when no scope_ids provided.
        Why this matters: Consistent behavior between sync and async methods.
        Setup summary: Mock SDK and call async search without scope_ids.
        """

        # Arrange
        async def async_return():
            return []

        mock_sdk.Search.create_async.return_value = async_return()

        # Act
        with patch("unique_toolkit.content.functions.logger") as mock_logger:
            await search_content_chunks_async(
                user_id="user123",
                company_id="company123",
                chat_id="chat123",
                search_string="test query",
                search_type=ContentSearchType.VECTOR,
                limit=10,
                scope_ids=None,
            )

        # Assert
        mock_logger.warning.assert_called_once()
        assert "No scope IDs provided" in str(mock_logger.warning.call_args)

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_search_contents__with_content_id_logging_AI(self, mock_sdk):
        """
        Purpose: Verify search_contents logs when contentId is in where clause.
        Why this matters: Helps with debugging specific content searches.
        Setup summary: Mock SDK and provide where clause with contentId.
        """
        # Arrange
        mock_sdk.Content.search.return_value = []
        where_clause = {"contentId": "content123"}

        # Act
        with patch("unique_toolkit.content.functions.logger") as mock_logger:
            search_contents(
                user_id="user123",
                company_id="company123",
                chat_id="chat123",
                where=where_clause,
            )

        # Assert
        mock_logger.info.assert_called_once()
        assert "content_id" in str(mock_logger.info.call_args)

    @pytest.mark.asyncio
    @patch("unique_toolkit.content.functions.unique_sdk")
    async def test_search_contents_async__with_content_id_logging_AI(self, mock_sdk):
        """
        Purpose: Verify async search_contents logs contentId parameter.
        Why this matters: Consistent logging between sync and async methods.
        Setup summary: Mock SDK and provide where clause with contentId.
        """

        # Arrange
        async def async_return():
            return []

        mock_sdk.Content.search_async.return_value = async_return()
        where_clause = {"contentId": "content123"}

        # Act
        with patch("unique_toolkit.content.functions.logger") as mock_logger:
            await search_contents_async(
                user_id="user123",
                company_id="company123",
                chat_id="chat123",
                where=where_clause,
            )

        # Assert
        mock_logger.info.assert_called_once()
        assert "content_id" in str(mock_logger.info.call_args)

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_upload_content__missing_read_url_error_AI(self, mock_sdk, tmp_path):
        """
        Purpose: Verify error handling when read_url is missing from upload response.
        Why this matters: Ensures proper error handling for malformed API responses.
        Setup summary: Mock SDK to return response without readUrl.
        """
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_sdk.Content.upsert.return_value = {
            "id": "content123",
            "writeUrl": "http://example.com/write",
            "readUrl": None,  # Missing readUrl
            "key": "test.txt",
            "title": "Test Document",
            "mimeType": "text/plain",
        }

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            upload_content(
                user_id="user123",
                company_id="company123",
                path_to_content=str(test_file),
                content_name="test.txt",
                mime_type="text/plain",
                scope_id="scope123",
            )
        assert "Read url for uploaded content is missing" in str(exc_info.value)

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_upload_content__error_handling_AI(self, mock_sdk, tmp_path):
        """
        Purpose: Verify error handling during upload process.
        Why this matters: Ensures graceful error handling for upload failures.
        Setup summary: Mock SDK to raise exception during upload.
        """
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_sdk.Content.upsert.side_effect = Exception("Upload failed")

        # Act & Assert
        with patch("unique_toolkit.content.functions.logger") as mock_logger:
            with pytest.raises(Exception) as exc_info:
                upload_content(
                    user_id="user123",
                    company_id="company123",
                    path_to_content=str(test_file),
                    content_name="test.txt",
                    mime_type="text/plain",
                    scope_id="scope123",
                )
            assert "Upload failed" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_upload_content_from_bytes__error_handling_AI(self, mock_sdk):
        """
        Purpose: Verify error handling during bytes upload process.
        Why this matters: Ensures graceful error handling for bytes upload failures.
        Setup summary: Mock SDK to raise exception during bytes upload.
        """
        # Arrange
        content = b"test content"
        mock_sdk.Content.upsert.side_effect = Exception("Upload failed")

        # Act & Assert
        with patch("unique_toolkit.content.functions.logger") as mock_logger:
            with pytest.raises(Exception) as exc_info:
                upload_content_from_bytes(
                    user_id="user123",
                    company_id="company123",
                    content=content,
                    content_name="test.txt",
                    mime_type="text/plain",
                    scope_id="scope123",
                )
            assert "Upload failed" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_download_content__error_handling_AI(self, mock_sdk):
        """
        Purpose: Verify error handling during download process.
        Why this matters: Ensures graceful error handling for download failures.
        Setup summary: Mock request_content_by_id to raise exception.
        """
        # Arrange
        with patch(
            "unique_toolkit.content.functions.request_content_by_id",
            side_effect=Exception("Download failed"),
        ):
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                download_content(
                    user_id="user123",
                    company_id="company123",
                    content_id="content123",
                    content_name="test.txt",
                    chat_id="chat123",
                )
            assert "Download failed" in str(exc_info.value)

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_download_content_to_bytes__error_handling_AI(self, mock_sdk):
        """
        Purpose: Verify error handling during bytes download process.
        Why this matters: Ensures graceful error handling for bytes download failures.
        Setup summary: Mock request_content_by_id to raise exception.
        """
        # Arrange
        with patch(
            "unique_toolkit.content.functions.request_content_by_id",
            side_effect=Exception("Download failed"),
        ):
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                download_content_to_bytes(
                    user_id="user123",
                    company_id="company123",
                    content_id="content123",
                    chat_id="chat123",
                )
            assert "Download failed" in str(exc_info.value)

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_download_content_to_file_by_id__error_handling_AI(self, mock_sdk):
        """
        Purpose: Verify error handling during file download process.
        Why this matters: Ensures graceful error handling for file download failures.
        Setup summary: Mock request_content_by_id to raise exception.
        """
        # Arrange
        with patch(
            "unique_toolkit.content.functions.request_content_by_id",
            side_effect=Exception("Download failed"),
        ):
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                download_content_to_file_by_id(
                    user_id="user123",
                    company_id="company123",
                    content_id="content123",
                    chat_id="chat123",
                )
            assert "Download failed" in str(exc_info.value)

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_trigger_upload_content__with_chat_id_AI(self, mock_sdk, tmp_path):
        """
        Purpose: Verify _trigger_upload_content works with chat_id parameter.
        Why this matters: Tests the internal upload logic with chat_id.
        Setup summary: Mock SDK and call _trigger_upload_content with chat_id.
        """
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_sdk.Content.upsert.return_value = {
            "id": "content123",
            "writeUrl": "http://example.com/write",
            "readUrl": "http://example.com/read",
            "key": "test.txt",
            "title": "Test Document",
            "mimeType": "text/plain",
        }

        # Act
        with patch("unique_toolkit.content.functions.requests.put") as mock_put:
            result = _trigger_upload_content(
                user_id="user123",
                company_id="company123",
                content=str(test_file),
                content_name="test.txt",
                mime_type="text/plain",
                chat_id="chat123",
            )

        # Assert
        assert isinstance(result, Content)
        assert result.id == "content123"
        mock_put.assert_called_once()

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_trigger_upload_content__with_scope_id_AI(self, mock_sdk, tmp_path):
        """
        Purpose: Verify _trigger_upload_content works with scope_id parameter.
        Why this matters: Tests the internal upload logic with scope_id.
        Setup summary: Mock SDK and call _trigger_upload_content with scope_id.
        """
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_sdk.Content.upsert.return_value = {
            "id": "content123",
            "writeUrl": "http://example.com/write",
            "readUrl": "http://example.com/read",
            "key": "test.txt",
            "title": "Test Document",
            "mimeType": "text/plain",
        }

        # Act
        with patch("unique_toolkit.content.functions.requests.put") as mock_put:
            result = _trigger_upload_content(
                user_id="user123",
                company_id="company123",
                content=str(test_file),
                content_name="test.txt",
                mime_type="text/plain",
                scope_id="scope123",
            )

        # Assert
        assert isinstance(result, Content)
        assert result.id == "content123"
        mock_put.assert_called_once()

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_trigger_upload_content__neither_chat_id_nor_scope_id_AI(
        self, mock_sdk, tmp_path
    ):
        """
        Purpose: Verify _trigger_upload_content raises error when neither chat_id nor scope_id provided.
        Why this matters: Ensures proper validation of required parameters.
        Setup summary: Call _trigger_upload_content without chat_id or scope_id.
        """
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            _trigger_upload_content(
                user_id="user123",
                company_id="company123",
                content=str(test_file),
                content_name="test.txt",
                mime_type="text/plain",
            )
        assert "chat_id or scope_id must be provided" in str(exc_info.value)

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_trigger_upload_content__with_bytes_content_AI(self, mock_sdk):
        """
        Purpose: Verify _trigger_upload_content works with bytes content.
        Why this matters: Tests the internal upload logic with bytes data.
        Setup summary: Mock SDK and call _trigger_upload_content with bytes.
        """
        # Arrange
        content = b"test content"
        mock_sdk.Content.upsert.return_value = {
            "id": "content123",
            "writeUrl": "http://example.com/write",
            "readUrl": "http://example.com/read",
            "key": "test.txt",
            "title": "Test Document",
            "mimeType": "text/plain",
        }

        # Act
        with patch("unique_toolkit.content.functions.requests.put") as mock_put:
            result = _trigger_upload_content(
                user_id="user123",
                company_id="company123",
                content=content,
                content_name="test.txt",
                mime_type="text/plain",
                scope_id="scope123",
            )

        # Assert
        assert isinstance(result, Content)
        assert result.id == "content123"
        mock_put.assert_called_once()

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_trigger_upload_content__with_skip_excel_ingestion_AI(
        self, mock_sdk, tmp_path
    ):
        """
        Purpose: Verify _trigger_upload_content handles skip_excel_ingestion flag.
        Why this matters: Tests ingestion configuration logic.
        Setup summary: Mock SDK and call with skip_excel_ingestion=True.
        """
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_sdk.Content.upsert.return_value = {
            "id": "content123",
            "writeUrl": "http://example.com/write",
            "readUrl": "http://example.com/read",
            "key": "test.txt",
            "title": "Test Document",
            "mimeType": "text/plain",
        }

        # Act
        with patch("unique_toolkit.content.functions.requests.put"):
            result = _trigger_upload_content(
                user_id="user123",
                company_id="company123",
                content=str(test_file),
                content_name="test.txt",
                mime_type="text/plain",
                scope_id="scope123",
                skip_excel_ingestion=True,
            )

        # Assert
        assert isinstance(result, Content)
        # Verify that the second upsert call includes the skip excel ingestion config
        assert mock_sdk.Content.upsert.call_count == 2
        second_call = mock_sdk.Content.upsert.call_args_list[1]
        assert (
            second_call[1]["input"]["ingestionConfig"]["uniqueIngestionMode"]
            == "SKIP_EXCEL_INGESTION"
        )

    @patch("unique_toolkit.content.functions.unique_sdk")
    def test_trigger_upload_content__with_skip_ingestion_AI(self, mock_sdk, tmp_path):
        """
        Purpose: Verify _trigger_upload_content handles skip_ingestion flag.
        Why this matters: Tests ingestion configuration logic.
        Setup summary: Mock SDK and call with skip_ingestion=True.
        """
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_sdk.Content.upsert.return_value = {
            "id": "content123",
            "writeUrl": "http://example.com/write",
            "readUrl": "http://example.com/read",
            "key": "test.txt",
            "title": "Test Document",
            "mimeType": "text/plain",
        }

        # Act
        with patch("unique_toolkit.content.functions.requests.put"):
            result = _trigger_upload_content(
                user_id="user123",
                company_id="company123",
                content=str(test_file),
                content_name="test.txt",
                mime_type="text/plain",
                scope_id="scope123",
                skip_ingestion=True,
            )

        # Assert
        assert isinstance(result, Content)
        # Verify that the second upsert call includes the skip ingestion config
        assert mock_sdk.Content.upsert.call_count == 2
        second_call = mock_sdk.Content.upsert.call_args_list[1]
        assert (
            second_call[1]["input"]["ingestionConfig"]["uniqueIngestionMode"]
            == "SKIP_INGESTION"
        )
