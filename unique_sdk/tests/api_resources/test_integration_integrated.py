from typing import List, cast

import pytest

from unique_sdk.api_resources._integrated import Integrated


@pytest.mark.integration
class TestIntegrated:
    def test_chat_stream_completion(self, event):
        """Test chat stream completion synchronously in sandbox."""
        messages = cast(
            List[Integrated.ChatCompletionRequestMessage],
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"},
            ],
        )

        search_context = cast(
            List[Integrated.SearchResult],
            [
                {
                    "id": "doc1",
                    "chunkId": "chunk1",
                    "key": "test-doc",
                    "title": "Test Document",
                    "url": "https://example.com/doc",
                }
            ],
        )

        response = Integrated.chat_stream_completion(
            user_id=event.user_id,
            company_id=event.company_id,
            messages=messages,
            searchContext=search_context,
            chatId=event.chat_id,
            assistantId="test-assistant",
            assistantMessageId=event.assistant_message_id,
            userMessageId=event.user_message_id,
            model="AZURE_GPT_4_0613",
        )
        assert isinstance(response.object, str)
        assert isinstance(response.message.id, str)
        assert response.message.chatId == event.chat_id
        assert isinstance(response.message.originalText, str)

    @pytest.mark.asyncio
    async def test_chat_stream_completion_async(self, event):
        """Test chat stream completion asynchronously in sandbox."""
        messages = cast(
            List[Integrated.ChatCompletionRequestMessage],
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"},
            ],
        )

        search_context = cast(
            List[Integrated.SearchResult],
            [
                {
                    "id": "doc1",
                    "chunkId": "chunk1",
                    "key": "test-doc",
                    "title": "Test Document",
                    "url": "https://example.com/doc",
                }
            ],
        )

        response = await Integrated.chat_stream_completion_async(
            user_id=event.user_id,
            company_id=event.company_id,
            messages=messages,
            searchContext=search_context,
            chatId=event.chat_id,
            assistantId="test-assistant",
            assistantMessageId=event.assistant_message_id,
            userMessageId=event.user_message_id,
            model="AZURE_GPT_4_0613",
        )

        assert isinstance(response.object, str)
        assert isinstance(response.message.id, str)
        assert response.message.chatId == event.chat_id
        assert isinstance(response.message.originalText, str)
