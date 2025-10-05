"""Tests for generator utility functions."""

from pathlib import Path

import pytest

from ...utils import (
    convert_path_to_snake_case,
    deduplicate_models,
    path_to_folder,
    resolve_refs,
    truncate_path,
)


class TestTruncatePath:
    """Tests for truncate_path utility."""

    @pytest.mark.ai_generated
    def test_truncate_path__shows_full_path__when_short_enough(self):
        """
        Purpose: Verify short paths are not truncated.
        Why: Users need to see full paths when they fit.
        Setup: Short path with 3 components.
        """
        # Arrange
        short_path = Path("folder/file.py")

        # Act
        result = truncate_path(short_path, max_parts=4)

        # Assert
        assert result == "folder/file.py"

    @pytest.mark.ai_generated
    def test_truncate_path__adds_ellipsis__when_too_long(self):
        """
        Purpose: Verify long paths are truncated with ... prefix.
        Why: Console output should be readable without wrapping.
        Setup: Path with 6 components, limit to 3.
        """
        # Arrange
        long_path = Path("a/b/c/d/e/file.py")

        # Act
        result = truncate_path(long_path, max_parts=3)

        # Assert
        assert result == ".../d/e/file.py"


class TestPathToFolder:
    """Tests for path_to_folder utility."""

    @pytest.mark.ai_generated
    def test_path_to_folder__removes_braces__from_path_params(self):
        """
        Purpose: Verify curly braces are removed from path parameters.
        Why: Folder names cannot contain curly braces.
        Setup: Path with {scopeId} parameter.
        """
        # Arrange
        api_path = "/public/folder/{scopeId}/access"

        # Act
        result = path_to_folder(api_path)

        # Assert
        assert result == Path("public/folder/scopeId/access")

    @pytest.mark.ai_generated
    def test_path_to_folder__converts_hyphens__to_underscores(self):
        """
        Purpose: Verify hyphens are converted to underscores.
        Why: Python module names cannot contain hyphens.
        Setup: Path with hyphenated segments.
        """
        # Arrange
        api_path = "/public/search-string"

        # Act
        result = path_to_folder(api_path)

        # Assert
        assert result == Path("public/search_string")


class TestConvertPathToSnakeCase:
    """Tests for convert_path_to_snake_case utility."""

    @pytest.mark.ai_generated
    def test_convert_path_to_snake_case__converts_camel_case_params__to_snake_case(
        self,
    ):
        """
        Purpose: Verify camelCase parameters are converted to snake_case.
        Why: Python conventions use snake_case for identifiers.
        Setup: Path with {scopeId} and {userId} parameters.
        """
        # Arrange
        path = "/public/folder/{scopeId}/user/{userId}"

        # Act
        result = convert_path_to_snake_case(path)

        # Assert
        assert result == "/public/folder/{scope_id}/user/{user_id}"

    @pytest.mark.ai_generated
    def test_convert_path_to_snake_case__preserves_non_param_segments__unchanged(
        self,
    ):
        """
        Purpose: Verify non-parameter path segments are not modified.
        Why: Only parameters need snake_case conversion.
        Setup: Mixed path with regular segments and parameters.
        """
        # Arrange
        path = "/public/messageLog/{logId}"

        # Act
        result = convert_path_to_snake_case(path)

        # Assert
        assert result == "/public/messageLog/{log_id}"


class TestDeduplicateModels:
    """Tests for deduplicate_models utility."""

    @pytest.mark.ai_generated
    def test_deduplicate_models__keeps_first_occurrence__of_identical_classes(self):
        """
        Purpose: Verify identical duplicate classes are removed.
        Why: Duplicate class definitions cause linter errors.
        Setup: Two identical Role enum definitions.
        """
        # Arrange
        model1 = "class Role(Enum):\n    user = 'USER'\n    admin = 'ADMIN'"
        model2 = "class Role(Enum):\n    user = 'USER'\n    admin = 'ADMIN'"
        models = [model1, "class Other(BaseModel):\n    pass", model2]

        # Act
        result = deduplicate_models(models)

        # Assert
        assert len(result) == 2
        assert result[0] == model1
        assert result[1] == "class Other(BaseModel):\n    pass"

    @pytest.mark.ai_generated
    def test_deduplicate_models__keeps_first__when_same_name_different_content(
        self, capsys
    ):
        """
        Purpose: Verify conflicts (same name, different content) keep first and warn.
        Why: Schema conflicts need visibility but shouldn't break generation.
        Setup: Two Status enums with different values.
        """
        # Arrange
        model1 = "class Status(Enum):\n    active = 'ACTIVE'"
        model2 = "class Status(Enum):\n    pending = 'PENDING'"
        models = [model1, model2]

        # Act
        result = deduplicate_models(models)
        captured = capsys.readouterr()

        # Assert
        assert len(result) == 1
        assert result[0] == model1
        assert "Warning: Duplicate class name 'Status'" in captured.out


class TestResolveRefs:
    """Tests for resolve_refs utility."""

    @pytest.mark.ai_generated
    def test_resolve_refs__resolves_dollar_ref__recursively(self, sample_openapi_spec):
        """
        Purpose: Verify $ref references are resolved to actual schemas.
        Why: Schema generation requires fully resolved schemas.
        Setup: Schema with $ref to TestResponse component.
        """
        # Arrange
        schema_with_ref = {"$ref": "#/components/schemas/TestResponse"}

        # Act
        result = resolve_refs(schema_with_ref, sample_openapi_spec)

        # Assert
        assert isinstance(result, dict)
        assert result["type"] == "object"
        assert "id" in result["properties"]
        assert "name" in result["properties"]

    @pytest.mark.ai_generated
    def test_resolve_refs__handles_nested_refs__in_properties(
        self, sample_openapi_spec
    ):
        """
        Purpose: Verify nested references in object properties are resolved.
        Why: Complex schemas often have nested component references.
        Setup: Schema with properties containing $ref.
        """
        # Arrange
        schema = {
            "type": "object",
            "properties": {"data": {"$ref": "#/components/schemas/TestResponse"}},
        }

        # Act
        result = resolve_refs(schema, sample_openapi_spec)

        # Assert
        assert isinstance(result["properties"]["data"], dict)
        assert result["properties"]["data"]["type"] == "object"
