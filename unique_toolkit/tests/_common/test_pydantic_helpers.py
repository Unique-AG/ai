"""
Unit tests for pydantic_helpers module.
"""

import warnings
from typing import Optional

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from unique_toolkit._common.pydantic_helpers import (
    create_complement_model,
    create_intersection_model,
    create_union_model,
    field_title_generator,
    get_configuration_dict,
    model_title_generator,
)


class TestFieldTitleGenerator:
    """Test cases for field_title_generator function."""

    def test_simple_camelcase_title(self):
        """Test converting camelCase to title case."""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo()
        result = field_title_generator("camelCaseField", field_info)
        assert result == "Camel Case Field"

    def test_snake_case_title(self):
        """Test converting snake_case to title case."""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo()
        result = field_title_generator("snake_case_field", field_info)
        assert result == "Snake Case Field"

    def test_mixed_case_title(self):
        """Test converting mixed case to title case."""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo()
        result = field_title_generator("mixedCaseField_name", field_info)
        assert result == "Mixed Case Field Name"

    def test_single_word_title(self):
        """Test single word title."""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo()
        result = field_title_generator("field", field_info)
        assert result == "Field"

    def test_empty_title(self):
        """Test empty title."""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo()
        result = field_title_generator("", field_info)
        assert result == ""

    def test_title_with_numbers(self):
        """Test title with numbers."""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo()
        result = field_title_generator("field123Name", field_info)
        assert result == "Field123 Name"


class TestModelTitleGenerator:
    """Test cases for model_title_generator function."""

    def test_simple_camelcase_model(self):
        """Test converting camelCase model name to title case."""

        class CamelCaseModel(BaseModel):
            pass

        result = model_title_generator(CamelCaseModel)
        assert result == "Camel Case Model"

    def test_snake_case_model(self):
        """Test converting snake_case model name to title case."""

        class snake_case_model(BaseModel):
            pass

        result = model_title_generator(snake_case_model)
        assert result == "Snake Case Model"

    def test_mixed_case_model(self):
        """Test converting mixed case model name to title case."""

        class MixedCaseModel_name(BaseModel):
            pass

        result = model_title_generator(MixedCaseModel_name)
        assert result == "Mixed Case Model Name"

    def test_single_word_model(self):
        """Test single word model name."""

        class Model(BaseModel):
            pass

        result = model_title_generator(Model)
        assert result == "Model"


class TestGetConfigurationDict:
    """Test cases for get_configuration_dict function."""

    def test_default_configuration(self):
        """Test default configuration dict."""
        config = get_configuration_dict()

        # ConfigDict is a TypedDict, so we can't use isinstance
        assert "field_title_generator" in config
        assert "model_title_generator" in config
        assert config["field_title_generator"] == field_title_generator
        assert config["model_title_generator"] == model_title_generator

    def test_configuration_with_additional_kwargs(self):
        """Test configuration dict with additional kwargs."""
        config = get_configuration_dict(
            populate_by_name=True, protected_namespaces=("protect",), extra="forbid"
        )

        # ConfigDict is a TypedDict, so we can't use isinstance
        assert "field_title_generator" in config
        assert "model_title_generator" in config
        assert config["field_title_generator"] == field_title_generator
        assert config["model_title_generator"] == model_title_generator
        assert config["populate_by_name"] is True
        assert config["protected_namespaces"] == ("protect",)
        assert config["extra"] == "forbid"

    def test_configuration_overrides(self):
        """Test that additional kwargs can override defaults."""

        def custom_field_title(title: str, info) -> str:
            return title.upper()

        config = get_configuration_dict(field_title_generator=custom_field_title)

        assert config["field_title_generator"] == custom_field_title
        assert config["model_title_generator"] == model_title_generator


class TestCreateUnionModel:
    """Test cases for create_union_model function."""

    def test_union_model_basic(self):
        """Test creating a union model with no overlapping fields."""

        class ModelA(BaseModel):
            field1: str = Field(default="a", description="Field 1")
            field2: int = Field(default=1, description="Field 2")

        class ModelB(BaseModel):
            field3: float = Field(default=3.14, description="Field 3")
            field4: bool = Field(default=True, description="Field 4")

        union_model = create_union_model(ModelA, ModelB, "UnionModel")

        # Check that all fields are present
        assert "field1" in union_model.model_fields
        assert "field2" in union_model.model_fields
        assert "field3" in union_model.model_fields
        assert "field4" in union_model.model_fields

        # Test instantiation
        instance = union_model()
        assert instance.field1 == "a"
        assert instance.field2 == 1
        assert instance.field3 == 3.14
        assert instance.field4 is True

    def test_union_model_with_overlapping_fields(self):
        """Test creating a union model with overlapping fields (should warn)."""

        class ModelA(BaseModel):
            field1: str = Field(default="a", description="Field 1 from A")
            field2: int = Field(default=1, description="Field 2 from A")

        class ModelB(BaseModel):
            field1: str = Field(default="b", description="Field 1 from B")
            field3: float = Field(default=3.14, description="Field 3")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            union_model = create_union_model(ModelA, ModelB, "UnionModel")

            # Should warn about overlapping fields
            assert len(w) == 1
            assert "common field names" in str(w[0].message)
            assert "field1" in str(w[0].message)

        # ModelA fields should take precedence
        instance = union_model()
        assert instance.field1 == "a"  # From ModelA
        assert instance.field2 == 1
        assert instance.field3 == 3.14

    def test_union_model_with_custom_config(self):
        """Test creating a union model with custom config."""

        class ModelA(BaseModel):
            field1: str

        class ModelB(BaseModel):
            field2: int

        custom_config = ConfigDict(extra="forbid")
        union_model = create_union_model(ModelA, ModelB, "UnionModel", custom_config)

        assert union_model.model_config["extra"] == "forbid"

    def test_union_model_field_precedence(self):
        """Test that ModelA fields take precedence over ModelB fields."""

        class ModelA(BaseModel):
            shared_field: str = Field(default="from_a", description="From A")

        class ModelB(BaseModel):
            shared_field: str = Field(default="from_b", description="From B")
            unique_field: int = Field(default=42, description="Unique to B")

        union_model = create_union_model(ModelA, ModelB, "UnionModel")

        instance = union_model()
        assert instance.shared_field == "from_a"  # ModelA takes precedence
        assert instance.unique_field == 42


class TestCreateIntersectionModel:
    """Test cases for create_intersection_model function."""

    def test_intersection_model_basic(self):
        """Test creating an intersection model with common fields."""

        class ModelA(BaseModel):
            field1: str = Field(default="a", description="Field 1 from A")
            field2: int = Field(default=1, description="Field 2 from A")
            field3: float = Field(default=1.0, description="Field 3 from A")

        class ModelB(BaseModel):
            field1: str = Field(default="b", description="Field 1 from B")
            field2: int = Field(default=2, description="Field 2 from B")
            field4: bool = Field(default=True, description="Field 4 from B")

        intersection_model = create_intersection_model(
            ModelA, ModelB, "IntersectionModel"
        )

        # Should only have common fields
        assert "field1" in intersection_model.model_fields
        assert "field2" in intersection_model.model_fields
        assert "field3" not in intersection_model.model_fields
        assert "field4" not in intersection_model.model_fields

        # Test instantiation
        instance = intersection_model()
        assert instance.field1 == "a"  # ModelA takes precedence
        assert instance.field2 == 1

    def test_intersection_model_no_common_fields(self):
        """Test creating an intersection model with no common fields (should warn)."""

        class ModelA(BaseModel):
            field1: str

        class ModelB(BaseModel):
            field2: int

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            intersection_model = create_intersection_model(
                ModelA, ModelB, "IntersectionModel"
            )

            # Should warn about no common fields
            assert len(w) == 1
            assert "no common field names" in str(w[0].message)

        # Should create empty model
        assert len(intersection_model.model_fields) == 0

    def test_intersection_model_with_custom_config(self):
        """Test creating an intersection model with custom config."""

        class ModelA(BaseModel):
            field1: str

        class ModelB(BaseModel):
            field1: str

        custom_config = ConfigDict(extra="forbid")
        intersection_model = create_intersection_model(
            ModelA, ModelB, "IntersectionModel", custom_config
        )

        assert intersection_model.model_config["extra"] == "forbid"

    def test_intersection_model_field_precedence(self):
        """Test that ModelA fields take precedence in intersection."""

        class ModelA(BaseModel):
            shared_field: str = Field(default="from_a", description="From A")

        class ModelB(BaseModel):
            shared_field: str = Field(default="from_b", description="From B")

        intersection_model = create_intersection_model(
            ModelA, ModelB, "IntersectionModel"
        )

        instance = intersection_model()
        assert instance.shared_field == "from_a"  # ModelA takes precedence


class TestCreateComplementModel:
    """Test cases for create_complement_model function."""

    def test_complement_model_basic(self):
        """Test creating a complement model (A - B)."""

        class ModelA(BaseModel):
            field1: str = Field(default="a", description="Field 1")
            field2: int = Field(default=1, description="Field 2")
            field3: float = Field(default=1.0, description="Field 3")

        class ModelB(BaseModel):
            field1: str = Field(default="b", description="Field 1")
            field4: bool = Field(default=True, description="Field 4")

        complement_model = create_complement_model(ModelA, ModelB, "ComplementModel")

        # Should only have fields from A that are not in B
        assert "field2" in complement_model.model_fields
        assert "field3" in complement_model.model_fields
        assert "field1" not in complement_model.model_fields  # Present in both
        assert "field4" not in complement_model.model_fields  # Not in A

        # Test instantiation
        instance = complement_model()
        assert instance.field2 == 1
        assert instance.field3 == 1.0

    def test_complement_model_no_common_fields(self):
        """Test creating a complement model with no common fields (should warn)."""

        class ModelA(BaseModel):
            field1: str

        class ModelB(BaseModel):
            field2: int

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            complement_model = create_complement_model(
                ModelA, ModelB, "ComplementModel"
            )

            # Should warn about no common fields
            assert len(w) == 1
            assert "no common field names" in str(w[0].message)

        # Should have all fields from A
        assert "field1" in complement_model.model_fields

    def test_complement_model_with_custom_config(self):
        """Test creating a complement model with custom config."""

        class ModelA(BaseModel):
            field1: str
            field2: int

        class ModelB(BaseModel):
            field1: str

        custom_config = ConfigDict(extra="forbid")
        complement_model = create_complement_model(
            ModelA, ModelB, "ComplementModel", custom_config
        )

        assert complement_model.model_config["extra"] == "forbid"

    def test_complement_model_all_fields_common(self):
        """Test complement model when all fields in A are also in B."""

        class ModelA(BaseModel):
            field1: str
            field2: int

        class ModelB(BaseModel):
            field1: str
            field2: int
            field3: float

        complement_model = create_complement_model(ModelA, ModelB, "ComplementModel")

        # Should have no fields
        assert len(complement_model.model_fields) == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_models_union(self):
        """Test union of empty models."""

        class EmptyModelA(BaseModel):
            pass

        class EmptyModelB(BaseModel):
            pass

        union_model = create_union_model(EmptyModelA, EmptyModelB, "EmptyUnion")
        assert len(union_model.model_fields) == 0

    def test_empty_models_intersection(self):
        """Test intersection of empty models."""

        class EmptyModelA(BaseModel):
            pass

        class EmptyModelB(BaseModel):
            pass

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            intersection_model = create_intersection_model(
                EmptyModelA, EmptyModelB, "EmptyIntersection"
            )

            # Should warn about no common fields
            assert len(w) == 1

        assert len(intersection_model.model_fields) == 0

    def test_empty_models_complement(self):
        """Test complement of empty models."""

        class EmptyModelA(BaseModel):
            pass

        class EmptyModelB(BaseModel):
            pass

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            complement_model = create_complement_model(
                EmptyModelA, EmptyModelB, "EmptyComplement"
            )

            # Should warn about no common fields
            assert len(w) == 1

        assert len(complement_model.model_fields) == 0

    def test_models_with_complex_field_types(self):
        """Test models with complex field types."""

        class ModelA(BaseModel):
            simple_field: str
            optional_field: Optional[str] = None
            list_field: list[str] = Field(default_factory=list)

        class ModelB(BaseModel):
            simple_field: str
            dict_field: dict[str, int] = Field(default_factory=dict)

        # Test union
        union_model = create_union_model(ModelA, ModelB, "ComplexUnion")
        assert "simple_field" in union_model.model_fields
        assert "optional_field" in union_model.model_fields
        assert "list_field" in union_model.model_fields
        assert "dict_field" in union_model.model_fields

        # Test intersection
        intersection_model = create_intersection_model(
            ModelA, ModelB, "ComplexIntersection"
        )
        assert "simple_field" in intersection_model.model_fields
        assert "optional_field" not in intersection_model.model_fields
        assert "list_field" not in intersection_model.model_fields
        assert "dict_field" not in intersection_model.model_fields

        # Test complement
        complement_model = create_complement_model(ModelA, ModelB, "ComplexComplement")
        assert "simple_field" not in complement_model.model_fields
        assert "optional_field" in complement_model.model_fields
        assert "list_field" in complement_model.model_fields
        assert "dict_field" not in complement_model.model_fields

    def test_models_with_different_field_annotations(self):
        """Test models with different field annotations but same names."""

        class ModelA(BaseModel):
            field1: str = Field(description="String field from A")

        class ModelB(BaseModel):
            field1: int = Field(description="Integer field from B")

        # Union should prefer ModelA (first model)
        union_model = create_union_model(ModelA, ModelB, "TypeUnion")
        field_info = union_model.model_fields["field1"]
        assert field_info.annotation is str  # Should be from ModelA

        # Test instantiation
        instance = union_model(field1="test")
        assert instance.field1 == "test"

    def test_generated_models_validation(self):
        """Test that generated models properly validate data."""

        class ModelA(BaseModel):
            name: str = Field(min_length=1, description="Name field")
            age: int = Field(ge=0, description="Age field")

        class ModelB(BaseModel):
            email: str = Field(
                pattern=r"^[^@]+@[^@]+\.[^@]+$", description="Email field"
            )

        union_model = create_union_model(ModelA, ModelB, "ValidationUnion")

        # Test valid data
        valid_instance = union_model(name="John", age=25, email="john@example.com")
        assert valid_instance.name == "John"
        assert valid_instance.age == 25
        assert valid_instance.email == "john@example.com"

        # Test invalid data (should raise ValidationError)
        with pytest.raises(ValidationError):
            union_model(name="", age=25, email="john@example.com")  # Empty name

        with pytest.raises(ValidationError):
            union_model(name="John", age=-1, email="john@example.com")  # Negative age

        with pytest.raises(ValidationError):
            union_model(name="John", age=25, email="invalid-email")  # Invalid email


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def test_user_profile_models(self):
        """Test combining user profile models."""

        class BasicUser(BaseModel):
            username: str = Field(description="Username")
            email: str = Field(description="Email address")

        class ExtendedUser(BaseModel):
            username: str = Field(description="Username")
            first_name: str = Field(description="First name")
            last_name: str = Field(description="Last name")
            phone: Optional[str] = Field(default=None, description="Phone number")

        class AdminUser(BaseModel):
            username: str = Field(description="Username")
            permissions: list[str] = Field(
                default_factory=list, description="Admin permissions"
            )
            is_superuser: bool = Field(default=False, description="Is superuser")

        # Create union of all user types
        all_users_model = create_union_model(
            create_union_model(BasicUser, ExtendedUser, "BasicExtendedUser"),
            AdminUser,
            "AllUsersModel",
        )

        # Should have all fields
        expected_fields = {
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "permissions",
            "is_superuser",
        }
        assert set(all_users_model.model_fields.keys()) == expected_fields

        # Test instantiation
        user = all_users_model(
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            phone="123-456-7890",
            permissions=["read", "write"],
            is_superuser=True,
        )
        assert user.username == "admin"
        assert user.email == "admin@example.com"
        assert user.first_name == "Admin"
        assert user.last_name == "User"
        assert user.phone == "123-456-7890"
        assert user.permissions == ["read", "write"]
        assert user.is_superuser is True

    def test_api_request_response_models(self):
        """Test combining API request and response models."""

        class CreateUserRequest(BaseModel):
            username: str = Field(description="Username")
            email: str = Field(description="Email address")
            password: str = Field(description="Password")

        class UserResponse(BaseModel):
            id: int = Field(description="User ID")
            username: str = Field(description="Username")
            email: str = Field(description="Email address")
            created_at: str = Field(description="Creation timestamp")

        class UpdateUserRequest(BaseModel):
            username: Optional[str] = Field(default=None, description="Username")
            email: Optional[str] = Field(default=None, description="Email address")

        # Create intersection of request and response (common fields)
        common_fields_model = create_intersection_model(
            CreateUserRequest, UserResponse, "CommonUserFields"
        )
        assert "username" in common_fields_model.model_fields
        assert "email" in common_fields_model.model_fields
        assert "password" not in common_fields_model.model_fields
        assert "id" not in common_fields_model.model_fields

        # Create complement of response minus request (response-only fields)
        response_only_model = create_complement_model(
            UserResponse, CreateUserRequest, "ResponseOnlyFields"
        )
        assert "id" in response_only_model.model_fields
        assert "created_at" in response_only_model.model_fields
        assert "username" not in response_only_model.model_fields
        assert "email" not in response_only_model.model_fields

    def test_configuration_inheritance(self):
        """Test that generated models inherit configuration properly."""

        class ModelA(BaseModel):
            field1: str

        class ModelB(BaseModel):
            field2: int

        # Test with custom configuration
        custom_config = ConfigDict(
            extra="forbid", validate_assignment=True, use_enum_values=True
        )

        union_model = create_union_model(ModelA, ModelB, "ConfigUnion", custom_config)

        assert union_model.model_config["extra"] == "forbid"
        assert union_model.model_config["validate_assignment"] is True
        assert union_model.model_config["use_enum_values"] is True
        # Note: Custom config doesn't automatically include title generators
        # This is expected behavior - the custom config overrides the default


if __name__ == "__main__":
    pytest.main([__file__])
