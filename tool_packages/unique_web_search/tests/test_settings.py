"""Tests for settings module validation changes."""

import json

import pytest

from unique_web_search.settings import CUSTOM_API_REQUEST_METHOD, Base


class TestSettingsValidateJSON:
    """Test cases for JSON validation field validator."""

    def test_validate_json_with_valid_json(self):
        """Test validate_json accepts valid JSON strings."""
        valid_headers = json.dumps({"Content-Type": "application/json"})
        settings = Base(custom_web_search_api_headers=valid_headers)

        assert settings.custom_web_search_api_headers == valid_headers
        if settings.custom_web_search_api_headers:
            assert json.loads(settings.custom_web_search_api_headers) == {
                "Content-Type": "application/json"
            }

    def test_validate_json_with_invalid_json_sets_none(self):
        """Test validate_json sets None for invalid JSON."""
        invalid_headers = "{'invalid': json}"  # Single quotes are invalid JSON
        settings = Base(custom_web_search_api_headers=invalid_headers)

        assert settings.custom_web_search_api_headers is None

    def test_validate_json_with_none_remains_none(self):
        """Test validate_json keeps None values."""
        settings = Base(custom_web_search_api_headers=None)
        assert settings.custom_web_search_api_headers is None

    def test_validate_json_all_custom_api_fields(self):
        """Test validate_json works for all custom API JSON fields."""
        valid_json = json.dumps({"key": "value"})
        invalid_json = "{broken"

        settings = Base(
            custom_web_search_api_headers=valid_json,
            custom_web_search_api_additional_query_params=invalid_json,
            custom_web_search_api_additional_body_params=valid_json,
            custom_web_search_api_client_config=invalid_json,
        )

        assert settings.custom_web_search_api_headers == valid_json
        assert settings.custom_web_search_api_additional_query_params is None
        assert settings.custom_web_search_api_additional_body_params == valid_json
        assert settings.custom_web_search_api_client_config is None


class TestCustomAPISettings:
    """Test cases for Custom API settings."""

    def test_custom_api_method_enum_values(self):
        """Test CUSTOM_API_REQUEST_METHOD enum values."""
        assert CUSTOM_API_REQUEST_METHOD.GET == "GET"
        assert CUSTOM_API_REQUEST_METHOD.POST == "POST"

    def test_custom_api_settings_defaults(self):
        """Test Custom API settings default to None."""
        settings = Base()

        assert settings.custom_web_search_api_method is None
        assert settings.custom_web_search_api_endpoint is None
        assert settings.custom_web_search_api_headers is None
        assert settings.custom_web_search_api_client_config is None

    def test_custom_api_settings_can_be_set(self):
        """Test Custom API settings can be configured."""
        headers = json.dumps({"Authorization": "Bearer token"})
        client_config = json.dumps({"timeout": 30})

        settings = Base(
            custom_web_search_api_method=CUSTOM_API_REQUEST_METHOD.POST,
            custom_web_search_api_endpoint="https://api.example.com",
            custom_web_search_api_headers=headers,
            custom_web_search_api_client_config=client_config,
        )

        assert settings.custom_web_search_api_method == CUSTOM_API_REQUEST_METHOD.POST
        assert settings.custom_web_search_api_endpoint == "https://api.example.com"
        assert settings.custom_web_search_api_headers == headers
        assert settings.custom_web_search_api_client_config == client_config


class TestValidateCustomWebSearchApiMethod:
    """Test cases for validate_custom_web_search_api_method field validator."""

    @pytest.mark.ai
    def test_validate_method__valid_get__returns_get_enum(self) -> None:
        """
        Purpose: Verify valid "GET" string is converted to CUSTOM_API_REQUEST_METHOD.GET.
        Why this matters: Ensures string config values are properly coerced to enum.
        Setup summary: Pass "GET" string; assert enum value.
        """
        # Act
        settings = Base(custom_web_search_api_method="GET")

        # Assert
        assert settings.custom_web_search_api_method == CUSTOM_API_REQUEST_METHOD.GET

    @pytest.mark.ai
    def test_validate_method__valid_post__returns_post_enum(self) -> None:
        """
        Purpose: Verify valid "POST" string is converted to CUSTOM_API_REQUEST_METHOD.POST.
        Why this matters: Ensures string config values are properly coerced to enum.
        Setup summary: Pass "POST" string; assert enum value.
        """
        # Act
        settings = Base(custom_web_search_api_method="POST")

        # Assert
        assert settings.custom_web_search_api_method == CUSTOM_API_REQUEST_METHOD.POST

    @pytest.mark.ai
    def test_validate_method__invalid_value__returns_none(self) -> None:
        """
        Purpose: Verify invalid method string is coerced to None instead of raising.
        Why this matters: Graceful degradation prevents startup failures from bad config.
        Setup summary: Pass invalid method string; assert None.
        """
        # Act
        settings = Base(custom_web_search_api_method="INVALID_METHOD")

        # Assert
        assert settings.custom_web_search_api_method is None

    @pytest.mark.ai
    def test_validate_method__none_value__remains_none(self) -> None:
        """
        Purpose: Verify None input is preserved as None.
        Why this matters: Default None must not be incorrectly coerced.
        Setup summary: Pass None; assert None.
        """
        # Act
        settings = Base(custom_web_search_api_method=None)

        # Assert
        assert settings.custom_web_search_api_method is None


class TestLLMProcessConfigSetting:
    """Test cases for llm_process_config JSON validation on Base settings."""

    @pytest.mark.ai
    def test_llm_process_config__valid_json__accepted(self) -> None:
        """
        Purpose: Verify valid JSON string for llm_process_config passes validation.
        Why this matters: IT admins provide JSON in .env to freeze LLM processor settings.
        Setup summary: Pass valid JSON; assert it is stored unchanged.
        """
        # Arrange
        valid_config = json.dumps({"enabled": True, "minTokens": 100})

        # Act
        settings = Base(llm_process_config=valid_config)

        # Assert
        assert settings.llm_process_config == valid_config
        assert json.loads(settings.llm_process_config) == {
            "enabled": True,
            "minTokens": 100,
        }

    @pytest.mark.ai
    def test_llm_process_config__invalid_json__set_to_none(self) -> None:
        """
        Purpose: Verify invalid JSON for llm_process_config is coerced to None.
        Why this matters: Malformed env config must not crash startup.
        Setup summary: Pass invalid JSON string; assert stored as None.
        """
        # Act
        settings = Base(llm_process_config="{broken json")

        # Assert
        assert settings.llm_process_config is None

    @pytest.mark.ai
    def test_llm_process_config__none__remains_none(self) -> None:
        """
        Purpose: Verify None input for llm_process_config stays None.
        Why this matters: Default None must not be incorrectly coerced.
        Setup summary: Pass None; assert None.
        """
        # Act
        settings = Base(llm_process_config=None)

        # Assert
        assert settings.llm_process_config is None


class TestAzureAISettings:
    """Test cases for Azure AI project settings fields."""

    @pytest.mark.ai
    def test_azure_ai_assistant_id__defaults_to_none(self) -> None:
        """
        Purpose: Verify azure_ai_assistant_id defaults to None.
        Why this matters: None default enables auto-provisioning fallback in Bing runner.
        Setup summary: Create default settings; assert field is None.
        """
        # Act
        settings = Base()

        # Assert
        assert settings.azure_ai_assistant_id is None

    @pytest.mark.ai
    def test_azure_ai_bing_agent_model__defaults_to_gpt4o_deployment(self) -> None:
        """
        Purpose: Verify azure_ai_bing_agent_model defaults to 'gpt-4o-deployment'.
        Why this matters: Deployment name changed from 'gpt-4o' to 'gpt-4o-deployment'.
        Setup summary: Create default settings; assert correct default.
        """
        # Act
        settings = Base()

        # Assert
        assert settings.azure_ai_bing_agent_model == "gpt-4o-deployment"

    @pytest.mark.ai
    def test_azure_ai_bing_resource_connection_string__exists_and_defaults_to_none(
        self,
    ) -> None:
        """
        Purpose: Verify the renamed field azure_ai_bing_resource_connection_string exists and defaults to None.
        Why this matters: The field was renamed from azure_ai_bing_ressource_connection_string (typo fix).
        Setup summary: Create default settings; assert field exists and is None.
        """
        # Act
        settings = Base()

        # Assert
        assert hasattr(settings, "azure_ai_bing_resource_connection_string")
        assert settings.azure_ai_bing_resource_connection_string is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
