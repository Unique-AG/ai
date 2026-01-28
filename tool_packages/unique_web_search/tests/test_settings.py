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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
