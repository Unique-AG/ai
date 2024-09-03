import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import ANY, Mock, patch

import pytest
import unique_sdk

from tests.test_obj_factory import get_event_obj
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentSearchType,
)
from unique_toolkit.content.service import ContentService


class TestContentServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.event = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )
        self.service = ContentService(self.event)

    def test_search_content_chunks(self):
        with patch.object(unique_sdk.Search, "create") as mock_create:
            mock_create.return_value = [
                {
                    "id": "1",
                    "text": "Test chunk",
                    "startPage": 1,
                    "endPage": 1,
                    "order": 1,
                }
            ]

            result = self.service.search_content_chunks(
                search_string="test",
                search_type=ContentSearchType.COMBINED,
                limit=10,
                scope_ids=["scope1", "scope2"],
            )

            assert isinstance(result, list)
            assert all(isinstance(chunk, ContentChunk) for chunk in result)
            assert len(result) == 1
            assert result[0].id == "1"
            assert result[0].text == "Test chunk"

            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
                searchString="test",
                searchType="COMBINED",
                scopeIds=["scope1", "scope2"],
                limit=10,
                reranker=None,
                language="english",
                chatOnly=None,
                metaDataFilter=None,
            )

    def test_search_contents(self):
        with patch.object(unique_sdk.Content, "search") as mock_search:
            mock_search.return_value = [
                {
                    "id": "1",
                    "key": "test_key",
                    "title": "Test Content",
                    "url": "http://test.com",
                    "chunks": [
                        {
                            "id": "chunk1",
                            "text": "Test chunk",
                            "startPage": 1,
                            "endPage": 1,
                            "order": 1,
                        }
                    ],
                    "createdAt": "2021-01-01T00:00:00Z",
                    "updatedAt": "2021-01-01T00:00:00Z",
                }
            ]

            result = self.service.search_contents(where={"key": "test_key"})

            assert isinstance(result, list)
            assert all(isinstance(content, Content) for content in result)
            assert len(result) == 1
            assert result[0].id == "1"
            assert result[0].key == "test_key"
            assert len(result[0].chunks) == 1
            assert result[0].chunks[0].id == "chunk1"

            mock_search.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
                where={"key": "test_key"},
            )

    def test_error_handling_search_content_chunks(self):
        with patch.object(
            unique_sdk.Search, "create", side_effect=Exception("API Error")
        ):
            with pytest.raises(Exception, match="API Error"):
                self.service.search_content_chunks(
                    "test", ContentSearchType.COMBINED, 10
                )

    def test_error_handling_search_contents(self):
        with patch.object(
            unique_sdk.Content, "search", side_effect=Exception("API Error")
        ):
            with pytest.raises(Exception, match="API Error"):
                self.service.search_contents({"key": "test_key"})

    @pytest.mark.asyncio
    async def test_search_content_chunks_async(self):
        with patch.object(unique_sdk.Search, "create_async") as mock_create:
            mock_create.return_value = [
                {
                    "id": "1",
                    "text": "Test chunk",
                    "startPage": 1,
                    "endPage": 1,
                    "order": 1,
                }
            ]

            result = await self.service.search_content_chunks_async(
                search_string="test",
                search_type=ContentSearchType.COMBINED,
                limit=10,
                scope_ids=["scope1", "scope2"],
            )

            assert isinstance(result, list)
            assert all(isinstance(chunk, ContentChunk) for chunk in result)
            assert len(result) == 1
            assert result[0].id == "1"
            assert result[0].text == "Test chunk"

            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
                searchString="test",
                searchType="COMBINED",
                scopeIds=["scope1", "scope2"],
                limit=10,
                reranker=None,
                language="english",
                chatOnly=None,
                metaDataFilter=None,
            )

    @pytest.mark.asyncio
    async def test_search_contents_async(self):
        with patch.object(unique_sdk.Content, "search_async") as mock_search:
            mock_search.return_value = [
                {
                    "id": "1",
                    "key": "test_key",
                    "title": "Test Content",
                    "url": "http://test.com",
                    "chunks": [
                        {
                            "id": "chunk1",
                            "text": "Test chunk",
                            "startPage": 1,
                            "endPage": 1,
                            "order": 1,
                        }
                    ],
                    "createdAt": "2021-01-01T00:00:00Z",
                    "updatedAt": "2021-01-01T00:00:00Z",
                }
            ]

            result = await self.service.search_contents_async(where={"key": "test_key"})

            assert isinstance(result, list)
            assert all(isinstance(content, Content) for content in result)
            assert len(result) == 1
            assert result[0].id == "1"
            assert result[0].key == "test_key"
            assert len(result[0].chunks) == 1
            assert result[0].chunks[0].id == "chunk1"

            mock_search.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
                where={"key": "test_key"},
            )

    @pytest.mark.asyncio
    async def test_error_handling_search_content_chunks_async(self):
        with patch.object(
            unique_sdk.Search, "create_async", side_effect=Exception("API Error")
        ):
            with pytest.raises(Exception, match="API Error"):
                await self.service.search_content_chunks_async(
                    "test", ContentSearchType.COMBINED, 10
                )

    @patch("requests.put")
    def test_upload_content(self, mock_put):
        with patch.object(unique_sdk.Content, "upsert") as mock_upsert:
            mock_upsert.return_value = {
                "id": "test_content_id",
                "key": "test.txt",
                "title": "test.txt",
                "mimeType": "text/plain",
                "byteSize": 100,
                "writeUrl": "http://test-write-url.com",
                "readUrl": "http://test-read-url.com",
            }
            # Create a temporary file for testing
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(b"Test content")
                temp_content_path = temp_file.name

            mock_upsert.side_effect = [
                {
                    "id": "test_content_id",
                    "key": "test.txt",
                    "title": "test.txt",
                    "mimeType": "text/plain",
                    "byteSize": 100,
                    "writeUrl": "http://test-write-url.com",
                    "readUrl": "http://test-read-url.com",
                },
                {
                    "id": "test_content_id",
                    "key": "test.txt",
                    "title": "test.txt",
                    "mimeType": "text/plain",
                    "byteSize": 100,
                    "writeUrl": "http://test-write-url.com",
                    "readUrl": "http://test-read-url.com",
                },
            ]

            result = self.service.upload_content(
                path_to_content=temp_content_path,
                content_name="test.txt",
                mime_type="text/plain",
                scope_id="test_scope",
            )

            assert isinstance(result, Content)
            assert result.id == "test_content_id"
            assert result.write_url == "http://test-write-url.com"
            assert result.read_url == "http://test-read-url.com"

            mock_put.assert_called_once_with(
                url="http://test-write-url.com",
                data=ANY,
                headers={
                    "X-Ms-Blob-Content-Type": "text/plain",
                    "X-Ms-Blob-Type": "BlockBlob",
                },
            )

            # Clean up the temporary file
            os.unlink(temp_content_path)

    @patch("requests.get")
    def test_download_content(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"Test content"
        mock_get.return_value = mock_response

        result = self.service.download_content(
            content_id="test_content_id",
            content_name="test.txt",
            chat_id="test_chat_id",
        )

        assert isinstance(result, Path)
        assert result.exists()
        assert result.name == "test.txt"
        assert result.read_bytes() == b"Test content"

        # Clean up the temporary file
        result.unlink()
        result.parent.rmdir()

    @patch("requests.get")
    def test_download_content_with_dir(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"Test content"
        mock_get.return_value = mock_response

        root_dir = Path("./tmp_root_dir")
        root_dir.mkdir(parents=True, exist_ok=True)

        result = self.service.download_content(
            content_id="test_content_id",
            content_name="test.txt",
            dir_path=root_dir,
        )

        assert isinstance(result, Path)
        assert result.exists()
        assert result.name == "test.txt"
        assert result.read_bytes() == b"Test content"
        assert (
            result.parent.parent.absolute().as_posix() == root_dir.absolute().as_posix()
        )

        result = self.service.download_content(
            content_id="test_content_id",
            content_name="test.txt",
            dir_path=root_dir.as_posix(),
        )

        assert isinstance(result, Path)
        assert result.exists()
        assert result.name == "test.txt"
        assert result.read_bytes() == b"Test content"
        assert (
            result.parent.parent.absolute().as_posix() == root_dir.absolute().as_posix()
        )

        # Clean up the temporary file
        result.unlink()
        shutil.rmtree(root_dir)
