from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from unique_toolkit.data_extraction.base import BaseDataExtractionResult
from unique_toolkit.data_extraction.basic import (
    StructuredOutputDataExtractor,
    StructuredOutputDataExtractorConfig,
)


class PersonModel(BaseModel):
    name: str
    age: int
    occupation: str = Field(default="Unknown")


class TestStructuredOutputDataExtractor:
    """Test the StructuredOutputDataExtractor class."""

    @pytest.fixture
    def mock_language_model_service(self):
        """Create a mock LanguageModelService."""
        mock_service = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()

        # Set up the mock response structure
        mock_message.parsed = {
            "name": "John Doe",
            "age": 30,
            "occupation": "Engineer",
        }
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_service.complete_async.return_value = mock_response

        return mock_service

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return StructuredOutputDataExtractorConfig()

    @pytest.fixture
    def extractor(self, config, mock_language_model_service):
        """Create a StructuredOutputDataExtractor instance."""
        return StructuredOutputDataExtractor(config, mock_language_model_service)

    @pytest.mark.asyncio
    async def test_extract_data_from_text_success(
        self, extractor, mock_language_model_service
    ):
        """Test successful data extraction from text."""
        text = "John Doe is 30 years old and works as an Engineer."

        result = await extractor.extract_data_from_text(text, PersonModel)

        # Verify the result
        assert isinstance(result, BaseDataExtractionResult)
        assert isinstance(result.data, PersonModel)
        assert result.data.name == "John Doe"
        assert result.data.age == 30
        assert result.data.occupation == "Engineer"

        # Verify the language model service was called correctly
        call_args = mock_language_model_service.complete_async.call_args
        assert call_args.kwargs["structured_output_model"] == PersonModel
        assert call_args.kwargs["structured_output_enforce_schema"] is False

    @pytest.mark.asyncio
    async def test_extract_data_with_enforce_schema(self, mock_language_model_service):
        """Test data extraction with schema enforcement enabled."""
        config = StructuredOutputDataExtractorConfig(
            structured_output_enforce_schema=True
        )
        extractor = StructuredOutputDataExtractor(config, mock_language_model_service)

        text = "Test text"
        await extractor.extract_data_from_text(text, PersonModel)

        # Verify schema enforcement was passed to the language model
        call_args = mock_language_model_service.complete_async.call_args
        assert call_args.kwargs["structured_output_enforce_schema"] is True
