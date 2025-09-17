"""
Unit tests for base_model_type_attribute module.
"""

import json
from typing import Annotated, Optional, Union

import pytest
from pydantic import BaseModel, Field

from unique_toolkit._common.base_model_type_attribute import (
    BaseModelTypeTitle,
    Parameter,
    ParameterType,
    base_model_to_parameter_list,
    convert_to_base_model_type,
    create_pydantic_model_from_parameter_list,
    get_json_schema_extra_for_base_model_type,
)


class TestParameterType:
    """Test cases for ParameterType enum."""

    def test_to_python_type_all_cases(self):
        """Test that all ParameterType values convert to correct Python types."""
        assert ParameterType.STRING.to_python_type() is str
        assert ParameterType.INTEGER.to_python_type() is int
        assert ParameterType.NUMBER.to_python_type() is float
        assert ParameterType.BOOLEAN.to_python_type() is bool

    def test_from_python_type_basic_types(self):
        """Test from_python_type with basic Python types."""
        assert ParameterType.from_python_type(str) == ParameterType.STRING
        assert ParameterType.from_python_type(int) == ParameterType.INTEGER
        assert ParameterType.from_python_type(float) == ParameterType.NUMBER
        assert ParameterType.from_python_type(bool) == ParameterType.BOOLEAN

    def test_from_python_type_annotated_types(self):
        """Test from_python_type with Annotated types."""
        # Test Annotated types with Field annotations
        assert (
            ParameterType.from_python_type(Annotated[str, Field(description="test")])  # type: ignore
            == ParameterType.STRING
        )  # type: ignore
        assert (
            ParameterType.from_python_type(Annotated[int, Field(description="test")])  # type: ignore
            == ParameterType.INTEGER
        )
        assert (
            ParameterType.from_python_type(Annotated[float, Field(description="test")])  # type: ignore
            == ParameterType.NUMBER
        )
        assert (
            ParameterType.from_python_type(Annotated[bool, Field(description="test")])  # type: ignore
            == ParameterType.BOOLEAN
        )

    def test_from_python_type_annotated_with_multiple_annotations(self):
        """Test Annotated types with multiple annotations."""
        annotated_str = Annotated[str, Field(description="test"), "extra_annotation"]
        assert ParameterType.from_python_type(annotated_str) == ParameterType.STRING  # type: ignore

    def test_from_python_type_optional_types(self):
        """Test from_python_type with Optional types."""
        assert ParameterType.from_python_type(Optional[str]) == ParameterType.STRING  # type: ignore
        assert ParameterType.from_python_type(Optional[int]) == ParameterType.INTEGER  # type: ignore

    def test_from_python_type_union_types(self):
        """Test from_python_type with Union types (should use first non-None type)."""
        assert ParameterType.from_python_type(Union[str, int]) == ParameterType.STRING  # type: ignore
        assert ParameterType.from_python_type(Union[int, str]) == ParameterType.INTEGER  # type: ignore

    def test_from_python_type_subclasses(self):
        """Test from_python_type with subclasses of basic types."""

        class CustomStr(str):
            pass

        class CustomInt(int):
            pass

        assert ParameterType.from_python_type(CustomStr) == ParameterType.STRING
        assert ParameterType.from_python_type(CustomInt) == ParameterType.INTEGER

    def test_from_python_type_bool_priority_over_int(self):
        """Test that bool is correctly identified as BOOLEAN, not INTEGER."""
        # This is important because bool is a subclass of int in Python
        assert ParameterType.from_python_type(bool) == ParameterType.BOOLEAN

    def test_from_python_type_invalid_types(self):
        """Test from_python_type with invalid types."""
        with pytest.raises(ValueError, match="Invalid Python type"):
            ParameterType.from_python_type(dict)

        with pytest.raises(ValueError, match="Invalid Python type"):
            ParameterType.from_python_type(list)

    def test_from_python_type_nested_annotated_types(self):
        """Test deeply nested Annotated types."""
        # Test Annotated[Optional[str], Field(...)]
        nested_type = Annotated[Optional[str], Field(description="optional string")]
        assert ParameterType.from_python_type(nested_type) == ParameterType.STRING  # type: ignore


class TestParameter:
    """Test cases for Parameter model."""

    def test_parameter_creation(self):
        """Test Parameter model creation."""
        param = Parameter(
            type=ParameterType.STRING,
            name="test_param",
            description="A test parameter",
            required=True,
        )
        assert param.type == ParameterType.STRING
        assert param.name == "test_param"
        assert param.description == "A test parameter"
        assert param.required is True

    def test_parameter_optional(self):
        """Test Parameter with optional field."""
        param = Parameter(
            type=ParameterType.INTEGER,
            name="optional_param",
            description="An optional parameter",
            required=False,
        )
        assert param.required is False


class TestCreatePydanticModelFromParameterList:
    """Test cases for create_pydantic_model_from_parameter_list function."""

    def test_create_model_with_required_fields(self):
        """Test creating a model with required fields."""
        parameters = [
            Parameter(
                type=ParameterType.STRING,
                name="name",
                description="User name",
                required=True,
            ),
            Parameter(
                type=ParameterType.INTEGER,
                name="age",
                description="User age",
                required=True,
            ),
        ]

        model_class = create_pydantic_model_from_parameter_list("TestModel", parameters)

        # Test that the model can be instantiated with required fields
        instance = model_class(name="John", age=30)
        assert instance.name == "John"  # type: ignore
        assert instance.age == 30  # type: ignore

        # Test that missing required fields raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            model_class(name="John")

    def test_create_model_with_optional_fields(self):
        """Test creating a model with optional fields."""
        parameters = [
            Parameter(
                type=ParameterType.STRING,
                name="name",
                description="User name",
                required=True,
            ),
            Parameter(
                type=ParameterType.STRING,
                name="nickname",
                description="User nickname",
                required=False,
            ),
        ]

        model_class = create_pydantic_model_from_parameter_list("TestModel", parameters)

        # Test with optional field
        instance = model_class(name="John", nickname="Johnny")
        assert instance.name == "John"  # type: ignore
        assert instance.nickname == "Johnny"  # type: ignore

        # Test without optional field
        instance = model_class(name="John")
        assert instance.name == "John"  # type: ignore
        assert instance.nickname is None  # type: ignore

    def test_create_model_all_types(self):
        """Test creating a model with all parameter types."""
        parameters = [
            Parameter(
                type=ParameterType.STRING,
                name="str_field",
                description="String field",
                required=True,
            ),
            Parameter(
                type=ParameterType.INTEGER,
                name="int_field",
                description="Integer field",
                required=True,
            ),
            Parameter(
                type=ParameterType.NUMBER,
                name="float_field",
                description="Float field",
                required=True,
            ),
            Parameter(
                type=ParameterType.BOOLEAN,
                name="bool_field",
                description="Boolean field",
                required=True,
            ),
        ]

        model_class = create_pydantic_model_from_parameter_list(
            "AllTypesModel", parameters
        )

        instance = model_class(
            str_field="test", int_field=42, float_field=3.14, bool_field=True
        )

        assert instance.str_field == "test"  # type: ignore
        assert instance.int_field == 42  # type: ignore
        assert instance.float_field == 3.14  # type: ignore
        assert instance.bool_field is True  # type: ignore


class TestConvertToBaseModelType:
    """Test cases for convert_to_base_model_type function."""

    def test_convert_existing_basemodel(self):
        """Test that existing BaseModel classes are returned as-is."""

        class TestModel(BaseModel):
            name: str

        result = convert_to_base_model_type(TestModel)
        assert result is TestModel

    def test_convert_parameter_list(self):
        """Test converting a list of Parameters to BaseModel."""
        parameters = [
            Parameter(
                type=ParameterType.STRING,
                name="name",
                description="User name",
                required=True,
            )
        ]

        result = convert_to_base_model_type(parameters)
        assert issubclass(result, BaseModel)

        # Test that the resulting model works
        instance = result(name="test")
        assert instance.name == "test"  # type: ignore

    def test_convert_json_schema_string(self):
        """Test converting JSON schema string to BaseModel."""
        schema = {
            "title": "TestSchema",
            "type": "object",
            "properties": {"name": {"type": "string", "description": "User name"}},
            "required": ["name"],
        }

        result = convert_to_base_model_type(json.dumps(schema))
        assert issubclass(result, BaseModel)

    def test_convert_invalid_value(self):
        """Test convert_to_base_model_type with invalid values."""
        with pytest.raises(ValueError, match="Invalid value"):
            convert_to_base_model_type(42)  # type: ignore

        with pytest.raises(ValueError, match="Invalid value"):
            convert_to_base_model_type([1, 2, 3])  # type: ignore  # List of non-Parameters


class TestBaseModelToParameterList:
    """Test cases for base_model_to_parameter_list function."""

    def test_convert_simple_model(self):
        """Test converting a simple BaseModel to parameter list."""

        class SimpleModel(BaseModel):
            name: str = Field(description="User name")
            age: int = Field(description="User age")

        parameters = base_model_to_parameter_list(SimpleModel)

        assert len(parameters) == 2

        name_param = next(p for p in parameters if p.name == "name")
        assert name_param.type == ParameterType.STRING
        assert name_param.description == "User name"
        assert name_param.required is True

        age_param = next(p for p in parameters if p.name == "age")
        assert age_param.type == ParameterType.INTEGER
        assert age_param.description == "User age"
        assert age_param.required is True

    def test_convert_model_with_optional_fields(self):
        """Test converting a model with optional fields."""

        class ModelWithOptional(BaseModel):
            name: str = Field(description="User name")
            nickname: Optional[str] = Field(default=None, description="User nickname")

        parameters = base_model_to_parameter_list(ModelWithOptional)

        name_param = next(p for p in parameters if p.name == "name")
        assert name_param.required is True

        nickname_param = next(p for p in parameters if p.name == "nickname")
        assert nickname_param.required is False

    def test_convert_model_with_annotated_fields(self):
        """Test converting a model with Annotated fields."""

        class ModelWithAnnotated(BaseModel):
            name: Annotated[str, Field(description="User name")]
            score: Annotated[float, Field(description="User score")]

        parameters = base_model_to_parameter_list(ModelWithAnnotated)

        assert len(parameters) == 2

        name_param = next(p for p in parameters if p.name == "name")
        assert name_param.type == ParameterType.STRING

        score_param = next(p for p in parameters if p.name == "score")
        assert score_param.type == ParameterType.NUMBER

    def test_convert_model_no_description(self):
        """Test converting a model where fields have no description."""

        class ModelNoDescription(BaseModel):
            name: str
            age: int

        parameters = base_model_to_parameter_list(ModelNoDescription)

        for param in parameters:
            assert param.description == ""


class TestGetJsonSchemaExtraForBaseModelType:
    """Test cases for get_json_schema_extra_for_base_model_type function."""

    def test_json_schema_extra_mutator(self):
        """Test that the mutator correctly adds defaults to schema."""

        class TestModel(BaseModel):
            name: str = Field(description="User name")

        mutator = get_json_schema_extra_for_base_model_type(TestModel)

        # Create a mock schema with oneOf structure
        schema = {
            "oneOf": [
                {
                    "type": "string",
                    "title": BaseModelTypeTitle.JSON_SCHEMA_AS_STRING.value,
                },
                {"type": "array", "title": BaseModelTypeTitle.LIST_OF_PARAMETERS.value},
            ]
        }

        mutator(schema)

        # Check that defaults were added
        string_entry = next(
            entry for entry in schema["oneOf"] if entry.get("type") == "string"
        )
        assert "default" in string_entry

        array_entry = next(
            entry for entry in schema["oneOf"] if entry.get("type") == "array"
        )
        assert "default" in array_entry
        assert isinstance(array_entry["default"], list)

    def test_json_schema_extra_with_anyof(self):
        """Test that the mutator works with anyOf structure."""

        class TestModel(BaseModel):
            name: str = Field(description="User name")

        mutator = get_json_schema_extra_for_base_model_type(TestModel)

        schema = {
            "anyOf": [
                {
                    "type": "string",
                    "title": BaseModelTypeTitle.JSON_SCHEMA_AS_STRING.value,
                }
            ]
        }

        mutator(schema)

        assert "default" in schema["anyOf"][0]


class TestBaseModelTypeIntegration:
    """Integration tests for the BaseModelType system."""

    def test_basemodel_type_with_existing_model(self):
        """Test BaseModelType with an existing BaseModel class."""

        class ExistingModel(BaseModel):
            name: str

        # This would typically be used in a Field definition
        converted = convert_to_base_model_type(ExistingModel)
        assert converted is ExistingModel

    def test_basemodel_type_with_parameter_list(self):
        """Test BaseModelType with a parameter list."""
        parameters = [
            Parameter(
                type=ParameterType.STRING,
                name="name",
                description="User name",
                required=True,
            )
        ]

        converted = convert_to_base_model_type(parameters)
        assert issubclass(converted, BaseModel)

        # Test that the resulting model works
        instance = converted(name="test")
        assert instance.name == "test"  # type: ignore

    def test_round_trip_conversion(self):
        """Test converting a BaseModel to parameters and back."""

        class OriginalModel(BaseModel):
            name: str = Field(description="User name")
            age: int = Field(description="User age")
            active: bool = Field(default=True, description="Is active")

        # Convert to parameters
        parameters = base_model_to_parameter_list(OriginalModel)

        # Convert back to model
        new_model = create_pydantic_model_from_parameter_list("NewModel", parameters)

        # Test that both models work similarly
        original_instance = OriginalModel(name="John", age=30)
        new_instance = new_model(name="John", age=30)

        assert original_instance.name == new_instance.name  # type: ignore
        assert original_instance.age == new_instance.age  # type: ignore


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_parameter_list(self):
        """Test creating a model from empty parameter list."""
        model_class = create_pydantic_model_from_parameter_list("EmptyModel", [])

        # Should create a model with no fields
        assert len(model_class.model_fields) == 0

    def test_parameter_with_underscore_in_name(self):
        """Test parameter with underscore in name."""
        param = Parameter(
            type=ParameterType.STRING,
            name="field_with_underscore",
            description="Test field",
            required=True,
        )

        model_class = create_pydantic_model_from_parameter_list("TestModel", [param])
        instance = model_class(field_with_underscore="test")
        assert instance.field_with_underscore == "test"  # type: ignore


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_mixed_field_types_and_annotations(self):
        """Test a model with mixed field types and annotations."""

        class ComplexModel(BaseModel):
            # Regular fields
            name: str = Field(description="User name")
            # Optional field
            email: Optional[str] = Field(default=None, description="User email")
            # Annotated field
            score: Annotated[float, Field(description="User score")]
            # Boolean field
            active: bool = Field(default=True, description="Is user active")

        parameters = base_model_to_parameter_list(ComplexModel)

        # Check we have all fields
        assert len(parameters) == 4

        # Check field types are correctly identified
        name_param = next(p for p in parameters if p.name == "name")
        assert name_param.type == ParameterType.STRING
        assert name_param.required is True

        email_param = next(p for p in parameters if p.name == "email")
        assert email_param.type == ParameterType.STRING
        assert email_param.required is False

        score_param = next(p for p in parameters if p.name == "score")
        assert score_param.type == ParameterType.NUMBER
        assert score_param.required is True

        active_param = next(p for p in parameters if p.name == "active")
        assert active_param.type == ParameterType.BOOLEAN
        assert active_param.required is False

    def test_convert_and_use_generated_model(self):
        """Test the full workflow of converting parameters to a usable model."""
        # Define parameters
        parameters = [
            Parameter(
                type=ParameterType.STRING,
                name="username",
                description="Username",
                required=True,
            ),
            Parameter(
                type=ParameterType.INTEGER,
                name="age",
                description="Age",
                required=False,
            ),
            Parameter(
                type=ParameterType.BOOLEAN,
                name="verified",
                description="Is verified",
                required=False,
            ),
        ]

        # Create model
        UserModel = create_pydantic_model_from_parameter_list("UserModel", parameters)

        # Test with all fields
        user1 = UserModel(username="alice", age=25, verified=True)
        assert user1.username == "alice"  # type: ignore
        assert user1.age == 25  # type: ignore
        assert user1.verified is True  # type: ignore

        # Test with only required fields
        user2 = UserModel(username="bob")
        assert user2.username == "bob"  # type: ignore
        assert user2.age is None  # type: ignore
        assert user2.verified is None  # type: ignore


if __name__ == "__main__":
    pytest.main([__file__])
