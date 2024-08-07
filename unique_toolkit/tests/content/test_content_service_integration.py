import os
import tempfile
from pathlib import Path

import pytest

from tests.conftest import test_scope_id
from unique_toolkit.app.schemas import Event
from unique_toolkit.content.schemas import Content, ContentChunk, ContentSearchType
from unique_toolkit.content.service import ContentService


@pytest.mark.usefixtures("event")
class TestContentServiceIntegration:
    @pytest.fixture(autouse=True)
    def setup(self, event: Event):
        self.event = event
        self.service = ContentService(event)

    def test_search_content_chunks(self):
        result = self.service.search_content_chunks(
            search_string="test",
            search_type=ContentSearchType.COMBINED,
            limit=10,
            scope_ids=["test_scope_id"],
        )

        assert isinstance(result, list)
        assert all(isinstance(chunk, ContentChunk) for chunk in result)
        assert len(result) > 0
        assert all(hasattr(chunk, "id") for chunk in result)
        assert all(hasattr(chunk, "text") for chunk in result)

    def test_search_contents(self):
        filter = [
            {
                "key": {
                    "equals": "test",
                },
                "ownerId": {
                    "equals": f"{[test_scope_id]}",
                },
            },
        ]

        where = {
            "OR": filter,
        }
        result = self.service.search_contents(where=where)

        assert isinstance(result, list)
        assert all(isinstance(content, Content) for content in result)
        if len(result) > 0:
            assert all(hasattr(content, "id") for content in result)
            assert all(hasattr(content, "key") for content in result)
            assert all(hasattr(content, "chunks") for content in result)
            assert all(isinstance(content.chunks, list) for content in result)
            assert all(hasattr(content, "createdAt") for content in result)
            assert all(hasattr(content, "updatedAt") for content in result)

    def test_error_handling(self):
        with pytest.raises(Exception):
            # This should raise an exception due to invalid search type
            self.service.search_content_chunks(
                search_string="test",
                search_type="invalid_type",  # type: ignore
                limit=10,
            )

    @pytest.mark.asyncio
    async def test_search_content_chunks_async(self):
        result = await self.service.search_content_chunks_async(
            search_string="test",
            search_type=ContentSearchType.COMBINED,
            limit=10,
            scope_ids=["test_scope_id"],
        )

        assert isinstance(result, list)
        assert all(isinstance(chunk, ContentChunk) for chunk in result)
        assert len(result) > 0
        assert all(hasattr(chunk, "id") for chunk in result)
        assert all(hasattr(chunk, "text") for chunk in result)

    @pytest.mark.asyncio
    async def test_search_contents_async(self):
        filter = [
            {
                "key": {
                    "equals": "test",
                },
                "ownerId": {
                    "equals": ["test_scope_id"],  # type: ignore
                },
            },
        ]

        where = {
            "OR": filter,
        }
        result = await self.service.search_contents_async(where=where)

        assert isinstance(result, list)
        assert all(isinstance(content, Content) for content in result)
        if len(result) > 0:
            assert all(hasattr(content, "id") for content in result)
            assert all(hasattr(content, "key") for content in result)
            assert all(hasattr(content, "chunks") for content in result)
            assert all(isinstance(content.chunks, list) for content in result)
            assert all(hasattr(content, "createdAt") for content in result)
            assert all(hasattr(content, "updatedAt") for content in result)

    @pytest.mark.asyncio
    async def test_error_handling_async(self):
        with pytest.raises(Exception):
            # This should raise an exception due to invalid search type
            await self.service.search_content_chunks_async(
                search_string="test",
                search_type="invalid_type",  # type: ignore
                limit=10,
            )

    def test_upload_and_download_content(self):
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content for integration")
            temp_file_path = temp_file.name

        try:
            # Test upload_content
            uploaded_content = self.service.upload_content(
                path_to_content=temp_file_path,
                content_name="integration_test.txt",
                mime_type="text/plain",
                scope_id=test_scope_id,
            )

            assert uploaded_content is not None
            assert uploaded_content.id is not None
            assert uploaded_content.key == "integration_test.txt"

            # Test download_content
            downloaded_path = self.service.download_content(
                content_id=uploaded_content.id,
                content_name="integration_test.txt",
                chat_id=None,
            )

            assert isinstance(downloaded_path, Path)
            assert downloaded_path.exists()
            assert downloaded_path.name == "integration_test.txt"

            with open(downloaded_path, "rb") as f:
                content = f.read()
                assert content == b"Test content for integration"

        finally:
            # Clean up
            os.unlink(temp_file_path)
            if "downloaded_path" in locals():
                downloaded_path.unlink()
                downloaded_path.parent.rmdir()

    def test_upload_content_with_chat_id(self):
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content for chat integration")
            temp_file_path = temp_file.name

        try:
            # Test upload_content with chat_id
            uploaded_content = self.service.upload_content(
                path_to_content=temp_file_path,
                content_name="chat_integration_test.txt",
                mime_type="text/plain",
                chat_id=self.event.payload.chat_id,
            )

            assert uploaded_content is not None
            assert uploaded_content.id is not None
            assert uploaded_content.key == "chat_integration_test.txt"

            # Test download_content with chat_id
            downloaded_path = self.service.download_content(
                content_id=uploaded_content.id,
                content_name="chat_integration_test.txt",
                chat_id=self.event.payload.chat_id,
            )

            assert isinstance(downloaded_path, Path)
            assert downloaded_path.exists()
            assert downloaded_path.name == "chat_integration_test.txt"

            with open(downloaded_path, "rb") as f:
                content = f.read()
                assert content == b"Test content for chat integration"

        finally:
            # Clean up
            os.unlink(temp_file_path)
            if "downloaded_path" in locals():
                downloaded_path.unlink()
                downloaded_path.parent.rmdir()
