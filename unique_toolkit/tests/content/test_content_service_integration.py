import os
import tempfile
import unittest
from pathlib import Path

import pytest

from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import Content, ContentChunk, ContentSearchType
from unique_toolkit.content.service import ContentService


@pytest.mark.usefixtures("chat_state")
class TestContentServiceIntegration(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def setup(self, chat_state: ChatState):
        self.state = chat_state
        self.service = ContentService(chat_state)

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
                    "equals": ["test_scope_id"],
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

    def test_error_handling(self):
        with pytest.raises(Exception):
            # This should raise an exception due to invalid search type
            self.service.search_content_chunks(
                search_string="test",
                search_type="invalid_type",  # type: ignore
                limit=10,
            )

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
            )

            self.assertIsNotNone(uploaded_content)
            self.assertIsNotNone(uploaded_content.id)
            self.assertEqual(uploaded_content.key, "integration_test.txt")

            # Test download_content
            downloaded_path = self.service.download_content(
                content_id=uploaded_content.id,
                content_name="integration_test.txt",
                chat_id=None,
            )

            self.assertIsInstance(downloaded_path, Path)
            self.assertTrue(downloaded_path.exists())
            self.assertEqual(downloaded_path.name, "integration_test.txt")

            with open(downloaded_path, "rb") as f:
                content = f.read()
                self.assertEqual(content, b"Test content for integration")

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
                chat_id=self.state.chat_id,
            )

            self.assertIsNotNone(uploaded_content)
            self.assertIsNotNone(uploaded_content.id)
            self.assertEqual(uploaded_content.key, "chat_integration_test.txt")

            # Test download_content with chat_id
            downloaded_path = self.service.download_content(
                content_id=uploaded_content.id,
                content_name="chat_integration_test.txt",
                chat_id=self.state.chat_id,
            )

            self.assertIsInstance(downloaded_path, Path)
            self.assertTrue(downloaded_path.exists())
            self.assertEqual(downloaded_path.name, "chat_integration_test.txt")

            with open(downloaded_path, "rb") as f:
                content = f.read()
                self.assertEqual(content, b"Test content for chat integration")

        finally:
            # Clean up
            os.unlink(temp_file_path)
            if "downloaded_path" in locals():
                downloaded_path.unlink()
                downloaded_path.parent.rmdir()
