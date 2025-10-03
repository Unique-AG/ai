from unittest.mock import patch

import pytest

from unique_toolkit.embedding.functions import (
    embed_texts,
    embed_texts_async,
)
from unique_toolkit.embedding.schemas import Embeddings


@pytest.fixture
def sample_embedding_data():
    """Sample embedding data for testing."""
    return {
        "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    }


@pytest.fixture
def sample_texts():
    """Sample texts for embedding."""
    return ["Hello world", "Test embedding"]


@pytest.mark.ai_generated
def test_embed_texts__returns_embeddings_object__when_successful_AI(
    sample_embedding_data, sample_texts
):
    """
    Purpose: Verify that embed_texts returns a proper Embeddings object with correct data.
    Why this matters: Core functionality for text embedding must work correctly.
    Setup summary: Mock SDK response with sample embedding data.
    """
    # Arrange
    with patch("unique_toolkit.embedding.functions.unique_sdk") as mock_sdk:
        mock_sdk.Embeddings.create.return_value = sample_embedding_data

        # Act
        result = embed_texts(
            user_id="user123",
            company_id="company123",
            texts=sample_texts,
            timeout=1000,
        )

        # Assert
        assert isinstance(result, Embeddings)
        assert result.embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_sdk.Embeddings.create.assert_called_once_with(
            user_id="user123",
            company_id="company123",
            texts=sample_texts,
            timeout=1000,
        )


@pytest.mark.ai_generated
@pytest.mark.asyncio
async def test_embed_texts_async__returns_embeddings_object__when_successful_AI(
    sample_embedding_data, sample_texts
):
    """
    Purpose: Verify that embed_texts_async returns a proper Embeddings object with correct data.
    Why this matters: Async embedding functionality must work correctly for non-blocking operations.
    Setup summary: Mock async SDK response with sample embedding data.
    """
    # Arrange
    with patch("unique_toolkit.embedding.functions.unique_sdk") as mock_sdk:

        async def async_mock(*args, **kwargs):
            return sample_embedding_data

        mock_sdk.Embeddings.create_async.side_effect = async_mock

        # Act
        result = await embed_texts_async(
            user_id="user123",
            company_id="company123",
            texts=sample_texts,
            timeout=1000,
        )

        # Assert
        assert isinstance(result, Embeddings)
        assert result.embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_sdk.Embeddings.create_async.assert_called_once_with(
            user_id="user123",
            company_id="company123",
            texts=sample_texts,
            timeout=1000,
        )


@pytest.mark.ai_generated
def test_embed_texts__raises_exception__when_sdk_error_AI(sample_texts):
    """
    Purpose: Verify that embed_texts properly propagates SDK errors.
    Why this matters: Error handling is critical for robust embedding functionality.
    Setup summary: Mock SDK to raise an exception.
    """
    # Arrange
    with patch("unique_toolkit.embedding.functions.unique_sdk") as mock_sdk:
        mock_sdk.Embeddings.create.side_effect = Exception("SDK error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            embed_texts(user_id="user123", company_id="company123", texts=sample_texts)
        assert str(exc_info.value) == "SDK error"


@pytest.mark.ai_generated
@pytest.mark.asyncio
async def test_embed_texts_async__raises_exception__when_sdk_error_AI(sample_texts):
    """
    Purpose: Verify that embed_texts_async properly propagates SDK errors.
    Why this matters: Async error handling is critical for robust embedding functionality.
    Setup summary: Mock async SDK to raise an exception.
    """
    # Arrange
    with patch("unique_toolkit.embedding.functions.unique_sdk") as mock_sdk:

        async def async_error(*args, **kwargs):
            raise Exception("SDK error")

        mock_sdk.Embeddings.create_async.side_effect = async_error

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await embed_texts_async(
                user_id="user123", company_id="company123", texts=sample_texts
            )
        assert str(exc_info.value) == "SDK error"


@pytest.mark.ai_generated
def test_embed_texts__handles_empty_input__when_texts_list_empty_AI():
    """
    Purpose: Verify that embed_texts handles empty text lists correctly.
    Why this matters: Edge case handling ensures robust embedding functionality.
    Setup summary: Mock SDK response for empty embeddings list.
    """
    # Arrange
    with patch("unique_toolkit.embedding.functions.unique_sdk") as mock_sdk:
        mock_sdk.Embeddings.create.return_value = {"embeddings": []}

        # Act
        result = embed_texts(user_id="user123", company_id="company123", texts=[])

        # Assert
        assert isinstance(result, Embeddings)
        assert result.embeddings == []
        mock_sdk.Embeddings.create.assert_called_once_with(
            user_id="user123",
            company_id="company123",
            texts=[],
            timeout=600000,  # Default timeout value
        )


@pytest.mark.ai_generated
@pytest.mark.asyncio
async def test_embed_texts_async__handles_empty_input__when_texts_list_empty_AI():
    """
    Purpose: Verify that embed_texts_async handles empty text lists correctly.
    Why this matters: Async edge case handling ensures robust embedding functionality.
    Setup summary: Mock async SDK response for empty embeddings list.
    """
    # Arrange
    with patch("unique_toolkit.embedding.functions.unique_sdk") as mock_sdk:

        async def async_mock(*args, **kwargs):
            return {"embeddings": []}

        mock_sdk.Embeddings.create_async.side_effect = async_mock

        # Act
        result = await embed_texts_async(
            user_id="user123", company_id="company123", texts=[]
        )

        # Assert
        assert isinstance(result, Embeddings)
        assert result.embeddings == []
