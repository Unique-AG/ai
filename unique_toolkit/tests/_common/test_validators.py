from pydantic import BaseModel

from unique_toolkit._common.validators import (
    LMI,
    get_LMI_default_field,
    serialize_lmi,
    validate_and_init_language_model_info,
)
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
)


class TestValidateAndInitLanguageModelInfo:
    """Tests for validate_and_init_language_model_info function."""

    def test_with_language_model_name_enum(self):
        """Test that LanguageModelName enum is converted to LanguageModelInfo."""
        result = validate_and_init_language_model_info(
            LanguageModelName.AZURE_GPT_4o_2024_1120
        )
        assert isinstance(result, LanguageModelInfo)
        assert result.name == LanguageModelName.AZURE_GPT_4o_2024_1120

    def test_with_string_model_name(self):
        """Test that string model name is converted to LanguageModelInfo."""
        result = validate_and_init_language_model_info("AZURE_GPT_4o_2024_1120")
        assert isinstance(result, LanguageModelInfo)
        assert result.name == LanguageModelName.AZURE_GPT_4o_2024_1120

    def test_with_custom_string_model_name(self):
        """Test that custom string creates a custom LanguageModelInfo."""
        result = validate_and_init_language_model_info("my-custom-model")
        assert isinstance(result, LanguageModelInfo)
        assert result.name == "my-custom-model"
        assert result.provider == LanguageModelProvider.CUSTOM

    def test_with_language_model_info_passthrough(self):
        """Test that LanguageModelInfo is returned as-is."""
        info = LanguageModelInfo(
            name="test-model",
            version="1.0",
            provider=LanguageModelProvider.CUSTOM,
        )
        result = validate_and_init_language_model_info(info)
        assert result is info


class TestSerializeLmi:
    """Tests for serialize_lmi function."""

    def test_serialize_non_custom_model(self):
        """Test that non-custom models serialize to their name."""
        info = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_1120)
        result = serialize_lmi(info)
        assert result == LanguageModelName.AZURE_GPT_4o_2024_1120

    def test_serialize_custom_model(self):
        """Test that custom models serialize to the full LanguageModelInfo."""
        info = LanguageModelInfo(
            name="custom-model",
            version="custom",
            provider=LanguageModelProvider.CUSTOM,
        )
        result = serialize_lmi(info)
        assert isinstance(result, LanguageModelInfo)
        assert result is info


class TestLMIAnnotation:
    """Tests for the LMI type annotation with Pydantic validation."""

    def test_lmi_with_language_model_name_enum(self):
        """Test LMI annotation with LanguageModelName enum."""

        class TestModel(BaseModel):
            model: LMI

        instance = TestModel(model=LanguageModelName.AZURE_GPT_4o_2024_1120)
        assert isinstance(instance.model, LanguageModelInfo)
        assert instance.model.name == LanguageModelName.AZURE_GPT_4o_2024_1120

    def test_lmi_with_string(self):
        """Test LMI annotation with string."""

        class TestModel(BaseModel):
            model: LMI

        instance = TestModel(model="AZURE_GPT_4o_2024_1120")
        assert isinstance(instance.model, LanguageModelInfo)
        assert instance.model.name == LanguageModelName.AZURE_GPT_4o_2024_1120

    def test_lmi_with_language_model_info(self):
        """Test LMI annotation with LanguageModelInfo."""

        class TestModel(BaseModel):
            model: LMI

        info = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_1120)
        instance = TestModel(model=info)
        assert isinstance(instance.model, LanguageModelInfo)
        assert instance.model is info

    def test_lmi_json_serialization_non_custom(self):
        """Test LMI JSON serialization for non-custom models."""

        class TestModel(BaseModel):
            model: LMI

        instance = TestModel(model=LanguageModelName.AZURE_GPT_4o_2024_1120)
        json_data = instance.model_dump(mode="json")
        assert json_data["model"] == LanguageModelName.AZURE_GPT_4o_2024_1120.value

    def test_lmi_json_serialization_custom(self):
        """Test LMI JSON serialization for custom models."""

        class TestModel(BaseModel):
            model: LMI

        info = LanguageModelInfo(
            name="custom-model",
            version="custom",
            provider=LanguageModelProvider.CUSTOM,
        )
        instance = TestModel(model=info)
        json_data = instance.model_dump(mode="json")
        assert isinstance(json_data["model"], dict)
        assert json_data["model"]["name"] == "custom-model"


class TestGetLMIDefaultField:
    """Tests for get_LMI_default_field function."""

    def test_creates_field_with_default(self):
        """Test that get_LMI_default_field creates a field with correct default."""

        class TestModel(BaseModel):
            model: LMI = get_LMI_default_field(LanguageModelName.AZURE_GPT_4o_2024_1120)

        instance = TestModel()
        assert isinstance(instance.model, LanguageModelInfo)
        assert instance.model.name == LanguageModelName.AZURE_GPT_4o_2024_1120

    def test_field_can_be_overridden(self):
        """Test that default field can be overridden."""

        class TestModel(BaseModel):
            model: LMI = get_LMI_default_field(LanguageModelName.AZURE_GPT_4o_2024_1120)

        instance = TestModel(model=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718)
        assert instance.model.name == LanguageModelName.AZURE_GPT_4o_MINI_2024_0718
