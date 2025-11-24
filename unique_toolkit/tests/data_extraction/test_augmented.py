from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field, create_model

from unique_toolkit.data_extraction.augmented import AugmentedDataExtractor
from unique_toolkit.data_extraction.augmented.service import (
    AugmentedDataExtractionResult,
    _build_augmented_model_for_field,
)
from unique_toolkit.data_extraction.base import (
    BaseDataExtractionResult,
    BaseDataExtractor,
)


class PersonModel(BaseModel):
    name: str
    age: int
    occupation: str = Field(default="Unknown")


class ContactModel(BaseModel):
    email: str
    phone: str


class TestAddExtraFields:
    """Test the _add_extra_fields helper function."""

    def test_add_single_extra_field(self):
        """Test adding a single extra field."""
        ModelWithExtra = _build_augmented_model_for_field("name", str, confidence=float)

        # Check that the model was created correctly
        assert ModelWithExtra.__name__ == "NameValue"
        assert "name" in ModelWithExtra.model_fields
        assert "confidence" in ModelWithExtra.model_fields

        # Test creating an instance
        instance = ModelWithExtra(name="John", confidence=0.95)
        assert getattr(instance, "name") == "John"
        assert getattr(instance, "confidence") == 0.95

    def test_add_multiple_extra_fields(self):
        """Test adding multiple extra fields."""
        ModelWithExtra = _build_augmented_model_for_field(
            "email",
            str,
            confidence=float,
            source=str,
            timestamp=(
                int,
                Field(default=0, description="Timestamp of the extraction"),
            ),
        )

        assert ModelWithExtra.__name__ == "EmailValue"
        assert "email" in ModelWithExtra.model_fields
        assert "confidence" in ModelWithExtra.model_fields
        assert "source" in ModelWithExtra.model_fields
        assert "timestamp" in ModelWithExtra.model_fields

        # Test with defaults
        instance = ModelWithExtra(
            email="test@example.com", confidence=0.8, source="llm"
        )
        assert getattr(instance, "email") == "test@example.com"
        assert getattr(instance, "confidence") == 0.8
        assert getattr(instance, "source") == "llm"
        assert getattr(instance, "timestamp") == 0
        assert (
            ModelWithExtra.model_fields["timestamp"].description
            == "Timestamp of the extraction"
        )

    def test_strict_mode_forbids_extra(self):
        """Test that strict mode forbids extra fields."""
        ModelWithExtra = _build_augmented_model_for_field(
            "name", str, strict=True, confidence=float
        )

        # Should work with expected fields
        instance = ModelWithExtra(name="John", confidence=0.95)
        assert getattr(instance, "name") == "John"

        # Should raise error with unexpected fields in strict mode
        with pytest.raises(ValueError):
            ModelWithExtra(name="John", confidence=0.95, unexpected_field="value")

    def test_non_strict_mode_allows_extra(self):
        """Test that non-strict mode allows extra fields."""
        ModelWithExtra = _build_augmented_model_for_field(
            "name", str, strict=False, confidence=float
        )

        # Should work with extra fields in non-strict mode
        instance = ModelWithExtra(name="John", confidence=0.95, extra_field="allowed")
        assert getattr(instance, "name") == "John"
        assert getattr(instance, "confidence") == 0.95
        assert not hasattr(instance, "extra_field")

    def test_field_with_field_info(self):
        """Test adding fields with FieldInfo objects."""
        field_info = Field(description="Confidence score", ge=0.0, le=1.0)
        ModelWithExtra = _build_augmented_model_for_field(
            "name", str, confidence=(float, field_info)
        )

        instance = ModelWithExtra(name="John", confidence=0.95)
        assert getattr(instance, "name") == "John"
        assert getattr(instance, "confidence") == 0.95

        # Test field validation
        with pytest.raises(ValueError):
            ModelWithExtra(name="John", confidence=1.5)  # Should fail ge/le constraint


class TestAugmentedDataExtractor:
    """Test the AugmentedDataExtractor class."""

    @pytest.fixture
    def mock_base_extractor(self):
        """Create a mock base data extractor."""
        mock_extractor = AsyncMock(spec=BaseDataExtractor)
        return mock_extractor

    def test_extractor_initialization(self, mock_base_extractor):
        """Test that the augmented extractor initializes correctly."""
        extractor = AugmentedDataExtractor(
            mock_base_extractor, confidence=float, source=str, strict=True
        )

        assert extractor._base_data_extractor == mock_base_extractor
        assert extractor._strict is True
        assert "confidence" in extractor._extra_fields
        assert "source" in extractor._extra_fields

    def test_prepare_schema_basic(self, mock_base_extractor):
        """Test schema preparation with basic fields."""
        extractor = AugmentedDataExtractor(mock_base_extractor, confidence=float)

        augmented_schema = extractor._prepare_schema(PersonModel)

        # Should have the same name as original schema
        assert augmented_schema.__name__ == PersonModel.__name__

        # Should have fields for each original field
        assert "name" in augmented_schema.model_fields
        assert "age" in augmented_schema.model_fields
        assert "occupation" in augmented_schema.model_fields

    def test_prepare_schema_with_multiple_extra_fields(self, mock_base_extractor):
        """Test schema preparation with multiple extra fields."""
        extractor = AugmentedDataExtractor(
            mock_base_extractor, confidence=float, source=str, timestamp=int
        )

        augmented_schema = extractor._prepare_schema(PersonModel)

        # Original schema should be augmented with extra fields for each original field
        assert augmented_schema.__name__ == PersonModel.__name__

        # The prepared schema should be a model where each field is wrapped
        # We can't easily test the internal structure without creating instances
        assert len(augmented_schema.model_fields) == len(PersonModel.model_fields)

    def test_extract_output_method(self, mock_base_extractor):
        """Test the _extract_output method."""
        extractor = AugmentedDataExtractor(mock_base_extractor, confidence=float)

        # Create a mock LLM output that simulates wrapped fields
        class MockWrappedName:
            name = "John"

        class MockWrappedAge:
            age = 30

        class MockWrappedOccupation:
            occupation = "Engineer"

        mock_llm_output = MagicMock()
        mock_llm_output.__iter__ = lambda x: iter(
            [
                ("name", MockWrappedName()),
                ("age", MockWrappedAge()),
                ("occupation", MockWrappedOccupation()),
            ]
        )

        result = extractor._extract_output(mock_llm_output, PersonModel)

        assert isinstance(result, PersonModel)
        assert result.name == "John"
        assert result.age == 30
        assert result.occupation == "Engineer"

    @pytest.mark.asyncio
    async def test_extract_data_from_text_success(self, mock_base_extractor):
        """Test successful augmented data extraction."""
        # Set up the mock base extractor
        mock_augmented_data = create_model("Mock")()
        mock_base_result = BaseDataExtractionResult(data=mock_augmented_data)
        mock_base_extractor.extract_data_from_text.return_value = mock_base_result

        extractor = AugmentedDataExtractor(mock_base_extractor, confidence=float)

        # Mock the _extract_output method to return expected data
        expected_data = PersonModel(name="John", age=30, occupation="Engineer")
        extractor._extract_output = MagicMock(return_value=expected_data)

        text = "John is 30 years old and works as an Engineer."
        result = await extractor.extract_data_from_text(text, PersonModel)

        # Verify the result
        assert isinstance(result, AugmentedDataExtractionResult)
        assert result.data == expected_data
        assert result.augmented_data == mock_augmented_data

        # Verify the base extractor was called with prepared schema
        mock_base_extractor.extract_data_from_text.assert_called_once()
        call_args = mock_base_extractor.extract_data_from_text.call_args
        assert call_args[0][0] == text  # First arg should be text
        # Second arg should be the prepared schema (we can't easily test the exact schema)

    @pytest.mark.asyncio
    async def test_extract_data_with_strict_mode(self, mock_base_extractor):
        """Test augmented extraction with strict mode enabled."""
        mock_augmented_data = create_model("Mock")()
        mock_base_result = BaseDataExtractionResult(data=mock_augmented_data)
        mock_base_extractor.extract_data_from_text.return_value = mock_base_result

        extractor = AugmentedDataExtractor(
            mock_base_extractor, strict=True, confidence=float
        )

        expected_data = PersonModel(name="Jane", age=25)
        extractor._extract_output = MagicMock(return_value=expected_data)

        text = "Jane is 25 years old."
        result = await extractor.extract_data_from_text(text, PersonModel)

        assert isinstance(result, AugmentedDataExtractionResult)
        assert result.data == expected_data
        assert extractor._strict is True

    def test_empty_extra_fields(self, mock_base_extractor):
        """Test extractor with no extra fields."""
        extractor = AugmentedDataExtractor(mock_base_extractor)

        assert extractor._extra_fields == {}
        assert extractor._strict is False

        # Should still be able to prepare schema
        schema = extractor._prepare_schema(PersonModel)
        assert schema is not None
