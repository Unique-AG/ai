from typing import cast

import pytest

from unique_sdk.api_resources._content import Content


@pytest.mark.integration
class TestContent:
    def test_search_content(self, event):
        """Test searching content synchronously in sandbox."""
        where_input = cast(
            Content.ContentWhereInput, {"ownerId": {"equals": event.user_id}}
        )

        response = Content.search(
            user_id=event.user_id, company_id=event.company_id, where=where_input
        )
        print(response, "where is the response")

        assert isinstance(response, list)
        if response:  # If any content exists
            content = response[0]
            assert isinstance(content.id, str)
            assert isinstance(content.key, str)
            assert isinstance(content.chunks, list)

    @pytest.mark.asyncio
    async def test_search_content_async(self, event):
        """Test searching content asynchronously in sandbox."""
        where_input = cast(
            Content.ContentWhereInput, {"ownerId": {"equals": event.user_id}}
        )

        response = await Content.search_async(
            user_id=event.user_id, company_id=event.company_id, where=where_input
        )

        assert isinstance(response, list)
        if response:  # If any content exists
            content = response[0]
            assert isinstance(content.id, str)
            assert isinstance(content.key, str)
            assert isinstance(content.chunks, list)

    @pytest.mark.unit
    def test_upsert_content(self, event):
        """Test upserting content synchronously in sandbox."""
        input_data = cast(
            Content.Input,
            {
                "key": "test-document",
                "title": "Test Document",
                "mimeType": "text/plain",
                "ownerType": "user",
                "byteSize": 100,
                "ingestionConfig": {"uniqueIngestionMode": "SKIP_INGESTION"},
            },
        )

        response = Content.upsert(
            user_id=event.user_id,
            company_id=event.company_id,
            input=input_data,
            chatId=event.chat_id,
            sourceOwnerType="user",
            storeInternally=True,
        )

        assert isinstance(response.id, str)
        assert isinstance(response.key, str)
        assert response.key == "test-document"
    
    @pytest.mark.unit
    def test_upsert_content_file_upload(self, event):
        """Test upserting content synchronously in sandbox."""
        input_data = cast(
            Content.Input,
            {
                "key": "test-document",
                "title": "Test Document 2",
                "mimeType": "text/plain",
                "ownerType": "user",
                "byteSize": 100,
                "ingestionConfig": {"uniqueIngestionMode": "SKIP_INGESTION"},
            },
        )

        response = Content.upsert(
            user_id=event.user_id,
            company_id=event.company_id,
            input=input_data,
            chatId=event.chat_id,
            sourceOwnerType="user",
            storeInternally=True,
            fileUrl="some_texts.txt"
        )

        assert isinstance(response.id, str)
        assert isinstance(response.key, str)
        assert response.key == "test-document"

    @pytest.mark.asyncio
    async def test_upsert_content_async(self, event):
        """Test upserting content asynchronously in sandbox."""
        input_data = cast(
            Content.Input,
            {
                "key": "test-document-async",
                "title": "Test Document Async",
                "mimeType": "text/plain",
                "ownerType": "user",
                "ownerId": event.user_id,
                "byteSize": 100,
                "ingestionConfig": {"uniqueIngestionMode": "default"},
            },
        )

        response = await Content.upsert_async(
            user_id=event.user_id,
            company_id=event.company_id,
            chatId=event.chat_id,
            input=input_data,
            sourceOwnerType="user",
            storeInternally=True,
        )
        assert isinstance(response.id, str)
        assert isinstance(response.key, str)
        assert response.key == "test-document-async"
