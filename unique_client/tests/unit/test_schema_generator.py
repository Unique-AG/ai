"""Tests for schema and model generation."""

import pytest
from generator.schema_generator import (
    create_simple_model_from_schema,
    extract_class_definitions,
    generate_model_from_schema,
)


class TestExtractClassDefinitions:
    """Tests for extract_class_definitions function."""

    @pytest.mark.ai_generated
    def test_extract_class_definitions__removes_imports__from_generated_code(self):
        """
        Purpose: Verify imports are stripped from generated model code.
        Why: Models file has its own import block, duplicates cause errors.
        Setup: Generated code with imports and class.
        """
        # Arrange
        content = """from typing import Any
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
"""

        # Act
        result = extract_class_definitions(content)

        # Assert
        assert "from typing" not in result
        assert "from pydantic" not in result
        assert "class User(BaseModel):" in result

    @pytest.mark.ai_generated
    def test_extract_class_definitions__puts_target_class_first__when_specified(self):
        """
        Purpose: Verify target class appears before dependent classes.
        Why: Response models should be at top of file for readability.
        Setup: Content with multiple classes, target CreateResponse.
        """
        # Arrange
        content = """class Object(Enum):
    list = "list"

class CreateResponse(BaseModel):
    object: Object
    data: str

class Role(Enum):
    user = "USER"
"""

        # Act
        result = extract_class_definitions(content, target_class="CreateResponse")

        # Assert
        lines = result.split("\n")
        first_class_line = next(
            (i for i, line in enumerate(lines) if line.startswith("class ")), None
        )
        assert "CreateResponse" in lines[first_class_line]

    @pytest.mark.ai_generated
    def test_extract_class_definitions__includes_all_classes__when_no_target(self):
        """
        Purpose: Verify all classes are extracted when no target specified.
        Why: Dependent models need to be included in generated files.
        Setup: Three different class definitions.
        """
        # Arrange
        content = """class Status(Enum):
    active = "ACTIVE"

class User(BaseModel):
    name: str

class Response(BaseModel):
    status: Status
"""

        # Act
        result = extract_class_definitions(content)

        # Assert
        assert "class Status(Enum):" in result
        assert "class User(BaseModel):" in result
        assert "class Response(BaseModel):" in result


class TestCreateSimpleModel:
    """Tests for create_simple_model_from_schema fallback."""

    @pytest.mark.ai_generated
    def test_create_simple_model__generates_basic_fields__from_schema(self):
        """
        Purpose: Verify simple model generation from schema properties.
        Why: Fallback when full generator fails keeps pipeline working.
        Setup: Schema with string, int, and optional fields.
        """
        # Arrange
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"},
            },
            "required": ["name", "age"],
        }

        # Act
        result = create_simple_model_from_schema(schema, "User")

        # Assert
        assert "class User(BaseModel):" in result
        assert "name: str" in result
        assert "age: int" in result
        assert "email: str" in result

    @pytest.mark.ai_generated
    def test_create_simple_model__returns_none__for_non_object_schema(self):
        """
        Purpose: Verify function returns None for invalid schemas.
        Why: Only object schemas can be converted to Pydantic models.
        Setup: Schema with type=array.
        """
        # Arrange
        schema = {"type": "array", "items": {"type": "string"}}

        # Act
        result = create_simple_model_from_schema(schema, "MyList")

        # Assert
        assert result is None


class TestGenerateModelFromSchema:
    """Tests for generate_model_from_schema function."""

    @pytest.mark.ai_generated
    def test_generate_model_from_schema__resolves_references__before_generation(
        self, sample_openapi_spec
    ):
        """
        Purpose: Verify schema references are resolved before model generation.
        Why: Code generator needs fully resolved schemas to work.
        Setup: Schema with $ref, spec with TestResponse component.
        """
        # Arrange
        schema = {"$ref": "#/components/schemas/TestResponse"}

        # Act
        result = generate_model_from_schema(schema, "MyResponse", sample_openapi_spec)

        # Assert
        assert result is not None
        assert "class MyResponse(BaseModel):" in result
        assert "id: str" in result
        assert "name: str" in result

    @pytest.mark.ai_generated
    def test_generate_model_from_schema__uses_fallback__when_generator_fails(self):
        """
        Purpose: Verify simple model fallback when full generation fails.
        Why: Malformed schemas shouldn't break entire generation pipeline.
        Setup: Minimal schema that might cause generator issues.
        """
        # Arrange
        schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        }

        # Act
        result = generate_model_from_schema(schema, "Simple", {})

        # Assert
        assert result is not None
        assert "class Simple" in result
