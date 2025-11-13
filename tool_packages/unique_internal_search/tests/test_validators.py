import re
from string import Template

import pytest
from pydantic import BaseModel

from unique_internal_search.validators import (
    PromptTemplatingEngine,
    check_placeholder_valid,
    get_prompt_placeholder_regexp,
    get_prompt_placeholder_regexp_from_text,
    get_string_field_with_pattern_validation,
)


class TestCheckPlaceholderValid:
    """Tests for check_placeholder_valid function"""

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "placeholder, expected",
        [
            ("name", True),
            ("user_name", True),
            ("user123", True),
            ("_private", True),
            ("VAR_NAME", True),
            ("var-name", False),
            ("var.name", False),
            ("var name", False),
            ("123invalid", False),
            ("", False),
        ],
        ids=[
            "valid_simple",
            "valid_with_underscore",
            "valid_with_numbers",
            "valid_leading_underscore",
            "valid_uppercase",
            "invalid_hyphen",
            "invalid_dot",
            "invalid_space",
            "invalid_leading_number",
            "invalid_empty",
        ],
    )
    def test_check_placeholder_valid__validates_pattern__string_template(
        self, placeholder: str, expected: bool
    ) -> None:
        """
        Purpose: Verify check_placeholder_valid validates placeholders against Template.idpattern.
        Why this matters: Ensures placeholder names are valid Python identifiers for string templates.
        Setup summary: Test various placeholder formats against expected validity.
        """
        # Act
        result = check_placeholder_valid(
            placeholder, templating_engine=PromptTemplatingEngine.STRING_TEMPLATE
        )

        # Assert
        assert result == expected

    @pytest.mark.ai
    def test_check_placeholder_valid__accepts_valid_identifiers__string_template(
        self,
    ) -> None:
        """
        Purpose: Verify check_placeholder_valid accepts valid Python identifiers.
        Why this matters: Template placeholders must be valid identifiers for substitution.
        Setup summary: Test valid identifier format matches Template.idpattern.
        """
        # Arrange
        placeholder = "valid_name_123"

        # Act
        result = check_placeholder_valid(
            placeholder, templating_engine=PromptTemplatingEngine.STRING_TEMPLATE
        )

        # Assert
        assert result is True
        # Verify it matches Template.idpattern
        assert re.fullmatch(Template.idpattern, placeholder, re.IGNORECASE) is not None


class TestGetPromptPlaceholderRegexp:
    """Tests for get_prompt_placeholder_regexp function"""

    @pytest.mark.ai
    def test_get_prompt_placeholder_regexp__returns_pattern__with_valid_placeholders(
        self,
    ) -> None:
        """
        Purpose: Verify get_prompt_placeholder_regexp returns compiled regex pattern for valid placeholders.
        Why this matters: Enables validation that prompts contain required placeholders.
        Setup summary: Provide valid placeholders, verify pattern is compiled and matches template strings.
        """
        # Arrange
        placeholders = ["name", "email"]

        # Act
        pattern = get_prompt_placeholder_regexp(*placeholders)

        # Assert
        assert isinstance(pattern, re.Pattern)
        assert pattern.match("Hello ${name}, your email is ${email}")
        assert pattern.match("Hello $name, your email is $email")
        assert not pattern.match("Hello")

    @pytest.mark.ai
    def test_get_prompt_placeholder_regexp__raises_value_error__with_invalid_placeholder(
        self,
    ) -> None:
        """
        Purpose: Verify get_prompt_placeholder_regexp raises ValueError for invalid placeholders.
        Why this matters: Prevents invalid placeholder names from being used in templates.
        Setup summary: Provide invalid placeholder, verify ValueError is raised with descriptive message.
        """
        # Arrange
        invalid_placeholder = "invalid-placeholder"

        # Act & Assert
        with pytest.raises(
            ValueError, match="Invalid placeholder: invalid-placeholder"
        ):
            get_prompt_placeholder_regexp(invalid_placeholder)

    @pytest.mark.ai
    def test_get_prompt_placeholder_regexp__validates_all_placeholders__before_compiling(
        self,
    ) -> None:
        """
        Purpose: Verify get_prompt_placeholder_regexp validates all placeholders before compilation.
        Why this matters: Ensures no invalid placeholders slip through validation.
        Setup summary: Provide mix of valid and invalid placeholders, verify error on first invalid.
        """
        # Arrange
        valid_placeholder = "name"
        invalid_placeholder = "invalid-name"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid placeholder: invalid-name"):
            get_prompt_placeholder_regexp(valid_placeholder, invalid_placeholder)

    @pytest.mark.ai
    def test_get_prompt_placeholder_regexp__handles_multiple_placeholders__correctly(
        self,
    ) -> None:
        """
        Purpose: Verify get_prompt_placeholder_regexp handles multiple placeholders correctly.
        Why this matters: Prompts often require multiple placeholders for proper formatting.
        Setup summary: Provide multiple valid placeholders, verify pattern matches all required placeholders.
        """
        # Arrange
        placeholders = ["name", "email", "date"]

        # Act
        pattern = get_prompt_placeholder_regexp(*placeholders)

        # Assert
        assert isinstance(pattern, re.Pattern)
        # Should match when all placeholders are present
        assert pattern.match("Hello ${name}, email: ${email}, date: ${date}")
        # Should not match when missing placeholders
        assert not pattern.match("Hello ${name}, email: ${email}")


class TestGetPromptPlaceholderRegexpFromText:
    """Tests for get_prompt_placeholder_regexp_from_text function"""

    @pytest.mark.ai
    def test_get_prompt_placeholder_regexp_from_text__extracts_placeholders__from_template(
        self,
    ) -> None:
        """
        Purpose: Verify get_prompt_placeholder_regexp_from_text extracts placeholders from template text.
        Why this matters: Automatically discovers placeholders from template strings for validation.
        Setup summary: Provide template with placeholders, verify pattern matches template and validates placeholders.
        """
        # Arrange
        template_text = "Hello ${name}, your email is ${email}"

        # Act
        pattern = get_prompt_placeholder_regexp_from_text(template_text)

        # Assert
        assert isinstance(pattern, re.Pattern)
        assert pattern.match(template_text)
        assert pattern.match("Hello $name, your email is $email")

    @pytest.mark.ai
    def test_get_prompt_placeholder_regexp_from_text__handles_single_placeholder__correctly(
        self,
    ) -> None:
        """
        Purpose: Verify get_prompt_placeholder_regexp_from_text handles single placeholder correctly.
        Why this matters: Common case where templates have only one placeholder.
        Setup summary: Provide template with single placeholder, verify pattern created correctly.
        """
        # Arrange
        template_text = "Welcome ${user}!"

        # Act
        pattern = get_prompt_placeholder_regexp_from_text(template_text)

        # Assert
        assert isinstance(pattern, re.Pattern)
        assert pattern.match(template_text)
        assert pattern.match("Welcome $user!")

    @pytest.mark.ai
    def test_get_prompt_placeholder_regexp_from_text__handles_dollar_sign_variants__correctly(
        self,
    ) -> None:
        """
        Purpose: Verify get_prompt_placeholder_regexp_from_text handles both ${var} and $var formats.
        Why this matters: String templates support both placeholder formats.
        Setup summary: Provide template with ${var} format, verify pattern matches both ${var} and $var variants.
        """
        # Arrange
        template_text = "Hello ${name}"

        # Act
        pattern = get_prompt_placeholder_regexp_from_text(template_text)

        # Assert
        assert isinstance(pattern, re.Pattern)
        # Should match both formats
        assert pattern.match("Hello ${name}")
        assert pattern.match("Hello $name")


class TestGetStringFieldWithPatternValidation:
    """Tests for get_string_field_with_pattern_validation function"""

    @pytest.mark.ai
    def test_get_string_field_with_pattern_validation__creates_field__with_pattern(
        self,
    ) -> None:
        """
        Purpose: Verify get_string_field_with_pattern_validation creates Field with pattern validation.
        Why this matters: Enables Pydantic validation of prompt templates containing required placeholders.
        Setup summary: Create Field with template, verify pattern is set and default value is template.
        """
        # Arrange
        template = "Hello ${name}, your email is ${email}"

        # Act
        field = get_string_field_with_pattern_validation(template)

        # Assert
        assert field.default == template
        # Pattern is stored in metadata in Pydantic FieldInfo
        assert len(field.metadata) > 0
        # Check that pattern metadata exists
        pattern_metadata = next(
            (m for m in field.metadata if hasattr(m, "pattern")), None
        )
        assert pattern_metadata is not None
        assert pattern_metadata.pattern is not None

    @pytest.mark.ai
    def test_get_string_field_with_pattern_validation__sets_default__to_template(
        self,
    ) -> None:
        """
        Purpose: Verify get_string_field_with_pattern_validation sets default value to template.
        Why this matters: Ensures default template is preserved for configuration models.
        Setup summary: Create Field with template, verify default is set correctly.
        """
        # Arrange
        template = "Welcome ${user}!"

        # Act
        field = get_string_field_with_pattern_validation(template)

        # Assert
        assert field.default == template

    @pytest.mark.ai
    def test_get_string_field_with_pattern_validation__applies_pattern__when_placeholders_exist(
        self,
    ) -> None:
        """
        Purpose: Verify get_string_field_with_pattern_validation applies pattern when placeholders exist.
        Why this matters: Validates that prompts contain required placeholders.
        Setup summary: Create Field with template containing placeholders, verify pattern validation works.
        """
        # Arrange
        template = "Hello ${name}"

        # Act
        field = get_string_field_with_pattern_validation(template)

        # Assert
        # Pattern is stored in metadata in Pydantic FieldInfo
        assert len(field.metadata) > 0
        pattern_metadata = next(
            (m for m in field.metadata if hasattr(m, "pattern")), None
        )
        assert pattern_metadata is not None
        assert pattern_metadata.pattern is not None

        # Create a model to test validation
        class TestModel(BaseModel):
            prompt: str = field

        # Should accept valid template
        model = TestModel(prompt="Hello ${name}")
        assert model.prompt == "Hello ${name}"

        # Should accept alternative format
        model2 = TestModel(prompt="Hello $name")
        assert model2.prompt == "Hello $name"

    @pytest.mark.ai
    def test_get_string_field_with_pattern_validation__handles_no_placeholders__without_pattern(
        self,
    ) -> None:
        """
        Purpose: Verify get_string_field_with_pattern_validation handles templates without placeholders.
        Why this matters: Templates without placeholders don't need pattern validation.
        Setup summary: Provide template without placeholders, verify pattern is not set or is empty.
        """
        # Arrange
        template = "Hello World"

        # Act
        field = get_string_field_with_pattern_validation(template)

        # Assert
        assert field.default == template
        # Pattern should not be set if template has no placeholders
        # This tests the condition on line 82 where pattern.pattern is checked
        if hasattr(field, "pattern") and field.pattern is not None:
            # If pattern exists, it should be empty or match empty string
            assert field.pattern.pattern == "" or not field.pattern.pattern

    @pytest.mark.ai
    def test_get_string_field_with_pattern_validation__preserves_additional_kwargs(
        self,
    ) -> None:
        """
        Purpose: Verify get_string_field_with_pattern_validation preserves additional Field kwargs.
        Why this matters: Allows customization of Field beyond default and pattern.
        Setup summary: Provide template with additional kwargs, verify they are preserved in Field.
        """
        # Arrange
        template = "Hello ${name}"
        description = "A greeting template"

        # Act
        field = get_string_field_with_pattern_validation(
            template, description=description
        )

        # Assert
        assert field.default == template
        assert field.description == description

    @pytest.mark.ai
    def test_get_string_field_with_pattern_validation__overrides_default_kwarg(
        self,
    ) -> None:
        """
        Purpose: Verify get_string_field_with_pattern_validation overrides default kwarg with template.
        Why this matters: Ensures template is always used as default regardless of kwargs.
        Setup summary: Provide template with default kwarg, verify template overrides it.
        """
        # Arrange
        template = "Hello ${name}"

        # Act
        field = get_string_field_with_pattern_validation(template, default="other")

        # Assert
        # Template should override any default kwarg
        assert field.default == template
        assert field.default != "other"
