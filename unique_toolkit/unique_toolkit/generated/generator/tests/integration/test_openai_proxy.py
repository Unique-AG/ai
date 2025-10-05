"""Integration tests for OpenAI proxy operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestOpenAIOperations:
    """Test OpenAI proxy operations."""

    def test_openai_chat_completions__generates_completion__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify OpenAI chat completions work through proxy.
        Why: Chat completions are primary AI interaction method.
        Setup: Request context with test data.
        """
        # Arrange
        # Act
        response = unique_SDK.openai.chat.completions.CreateChatCompletion.request(
            context=request_context,
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in one word."},
            ],
            max_tokens=10,
        )

        # Assert
        assert response is not None
        # Response should have choices
        if hasattr(response, "choices"):
            assert len(response.choices) > 0
        elif isinstance(response, dict):
            assert "choices" in response

    def test_openai_embeddings__generates_embeddings__successfully(
        self, request_context
    ):
        """
        Purpose: Verify embeddings generation works through proxy.
        Why: Embeddings are essential for semantic search.
        Setup: Request context with test text.
        """
        # Act
        response = unique_SDK.openai.embeddings.CreateEmbedding.request(
            context=request_context,
            input="Integration test text",
            model="text-embedding-ada-002",
        )

        # Assert
        assert response is not None
        if hasattr(response, "data"):
            assert len(response.data) > 0
        elif isinstance(response, dict):
            assert "data" in response
