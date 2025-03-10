from typing import List, cast

import pytest

from unique_sdk.api_resources._chat_completion import (
    ChatCompletion,
    ChatCompletionRequestMessage,
)


@pytest.mark.integration
class TestChatCompletion:
    messages = cast(
        List[ChatCompletionRequestMessage],
        [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?", "name": "Alice"},
            {
                "role": "assistant",
                "content": "I'm doing great! How can I assist you?",
                "tool_call_id": "12345",
            },
            {"role": "user", "content": "Tell me a joke."},
            {
                "role": "assistant",
                "content": "Sure! Why did the chicken join a band? Because it had the drumsticks!",
            },
        ],
    )

    def test_create_chat_completion(self, event):
        """Test creating chat completion synchronously in sandbox."""
        response = ChatCompletion.create(
            company_id=event.company_id,
            messages=self.messages,
            model="AZURE_GPT_4_0613",
        )
        assert isinstance(response, dict)
        assert "systemFingerprint" in response
        assert "choices" in response
        assert isinstance(response.choices, list)
        for choice in response.choices:
            assert "message" in choice
            assert "index" in choice

    @pytest.mark.asyncio
    async def test_create_chat_completion_async(self, event):
        """Test creating chat completion asynchronously in sandbox."""

        response = await ChatCompletion.create_async(
            company_id=event.company_id,
            messages=self.messages,
            model="AZURE_GPT_4_0613",
        )

        assert isinstance(response, dict)
        assert "systemFingerprint" in response
        assert "choices" in response
        assert isinstance(response.choices, list)
        for choice in response.choices:
            assert "message" in choice
            assert "index" in choice
