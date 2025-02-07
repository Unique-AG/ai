from unittest.mock import Mock, patch

import pytest

from unique_toolkit.embedding.functions import (
    embed_texts,
    embed_texts_async,
)
from unique_toolkit.embedding.schemas import Embeddings


@pytest.fixture
def mock_sdk():
    with patch("unique_toolkit.embedding.functions.unique_sdk") as mock:
        yield mock


@pytest.fixture
def sample_embedding_data():
    return {
        "id": "emb123",
        "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    }


def test_embed_texts(mock_sdk, sample_embedding_data):
    # Setup
    mock_sdk.Embeddings.create.return_value = sample_embedding_data

    # Execute
    result = embed_texts(
        user_id="user123",
        company_id="company123",
        texts=["text1", "text2"],
        timeout=1000,
    )

    # Assert
    assert isinstance(result, Embeddings)
    mock_sdk.Embeddings.create.assert_called_once_with(
        user_id="user123",
        company_id="company123",
        texts=["text1", "text2"],
        timeout=1000,
    )
    assert result.embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


@pytest.mark.asyncio
async def test_embed_texts_async(mock_sdk, sample_embedding_data):
    # Setup
    mock_response = Mock()
    mock_response.return_value = sample_embedding_data

    async def async_mock(*args, **kwargs):
        return sample_embedding_data

    mock_sdk.Embeddings.create_async.side_effect = async_mock

    # Execute
    result = await embed_texts_async(
        user_id="user123",
        company_id="company123",
        texts=["text1", "text2"],
        timeout=1000,
    )

    # Assert
    assert isinstance(result, Embeddings)
    mock_sdk.Embeddings.create_async.assert_called_once_with(
        user_id="user123",
        company_id="company123",
        texts=["text1", "text2"],
        timeout=1000,
    )
    assert result.embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_embed_texts_error(mock_sdk):
    # Setup
    mock_sdk.Embeddings.create.side_effect = Exception("SDK error")

    # Execute & Assert
    with pytest.raises(Exception) as exc_info:
        embed_texts(
            user_id="user123", company_id="company123", texts=["text1", "text2"]
        )
    assert str(exc_info.value) == "SDK error"


@pytest.mark.asyncio
async def test_embed_texts_async_error(mock_sdk):
    # Setup
    async def async_error(*args, **kwargs):
        raise Exception("SDK error")

    mock_sdk.Embeddings.create_async.side_effect = async_error

    # Execute & Assert
    with pytest.raises(Exception) as exc_info:
        await embed_texts_async(
            user_id="user123", company_id="company123", texts=["text1", "text2"]
        )
    assert str(exc_info.value) == "SDK error"


def test_embed_texts_empty_input(mock_sdk):
    # Setup
    mock_sdk.Embeddings.create.return_value = {
        "id": "emb123",
        "embeddings": [],  # Empty embeddings list but still a valid response
    }

    # Execute
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


@pytest.mark.asyncio
async def test_embed_texts_async_empty_input(mock_sdk):
    # Setup
    async def async_mock(*args, **kwargs):
        return {"embeddings": []}

    mock_sdk.Embeddings.create_async.side_effect = async_mock

    # Execute
    result = await embed_texts_async(
        user_id="user123", company_id="company123", texts=[]
    )

    # Assert
    assert isinstance(result, Embeddings)
    assert result.embeddings == []
