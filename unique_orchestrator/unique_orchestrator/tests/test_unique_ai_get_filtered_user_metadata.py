from unittest.mock import MagicMock

import pytest


class TestGetFilteredUserMetadata:
    """Test suite for UniqueAI._get_filtered_user_metadata method"""

    @pytest.fixture
    def mock_unique_ai(self):
        """Create a minimal UniqueAI instance with mocked dependencies"""
        # Lazy import to avoid heavy dependencies at module import time
        from unique_orchestrator.unique_ai import UniqueAI

        mock_logger = MagicMock()

        # Create minimal event structure
        dummy_event = MagicMock()
        dummy_event.payload.assistant_message.id = "assist_1"
        dummy_event.payload.user_message.text = "query"

        # Create minimal config structure
        mock_config = MagicMock()
        mock_config.agent.prompt_config.user_metadata = []

        # Create minimal required dependencies
        mock_chat_service = MagicMock()
        mock_content_service = MagicMock()
        mock_debug_info_manager = MagicMock()
        mock_reference_manager = MagicMock()
        mock_thinking_manager = MagicMock()
        mock_tool_manager = MagicMock()
        mock_history_manager = MagicMock()
        mock_evaluation_manager = MagicMock()
        mock_postprocessor_manager = MagicMock()
        mock_streaming_handler = MagicMock()
        mock_message_step_logger = MagicMock()
        mock_loop_iteration_runner = MagicMock()

        # Instantiate UniqueAI
        ua = UniqueAI(
            logger=mock_logger,
            event=dummy_event,
            config=mock_config,
            chat_service=mock_chat_service,
            content_service=mock_content_service,
            debug_info_manager=mock_debug_info_manager,
            streaming_handler=mock_streaming_handler,
            reference_manager=mock_reference_manager,
            thinking_manager=mock_thinking_manager,
            tool_manager=mock_tool_manager,
            history_manager=mock_history_manager,
            evaluation_manager=mock_evaluation_manager,
            postprocessor_manager=mock_postprocessor_manager,
            message_step_logger=mock_message_step_logger,
            mcp_servers=[],
            loop_iteration_runner=mock_loop_iteration_runner,
        )

        return ua

    def test_returns_empty_dict_when_config_is_empty_list(self, mock_unique_ai):
        """Test that empty dict is returned when config.user_metadata is an empty list"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = []
        mock_unique_ai._event.payload.user_metadata = {
            "department": "Engineering",
            "role": "Developer",
        }

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {}
        assert isinstance(result, dict)

    def test_returns_empty_dict_when_user_metadata_is_none(self, mock_unique_ai):
        """Test that empty dict is returned when user_metadata is None"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = [
            "department",
            "role",
        ]
        mock_unique_ai._event.payload.user_metadata = None

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {}
        assert isinstance(result, dict)

    def test_returns_empty_dict_when_both_config_and_metadata_are_empty(
        self, mock_unique_ai
    ):
        """Test that empty dict is returned when both config and user_metadata are empty/None"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = []
        mock_unique_ai._event.payload.user_metadata = None

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {}
        assert isinstance(result, dict)

    def test_filters_metadata_to_include_only_configured_keys(self, mock_unique_ai):
        """Test that only keys specified in config are included in the result"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = [
            "department",
            "role",
        ]
        mock_unique_ai._event.payload.user_metadata = {
            "department": "Engineering",
            "role": "Developer",
            "location": "San Francisco",
            "salary": "100000",
        }

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {"department": "Engineering", "role": "Developer"}
        assert "location" not in result
        assert "salary" not in result
        # Verify all values are strings
        assert all(isinstance(v, str) for v in result.values())

    def test_returns_only_existing_keys_from_user_metadata(self, mock_unique_ai):
        """Test that keys in config but not in user_metadata are not included"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = [
            "department",
            "role",
            "team",
            "manager",
        ]
        mock_unique_ai._event.payload.user_metadata = {
            "department": "Engineering",
            "role": "Developer",
        }

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {"department": "Engineering", "role": "Developer"}
        assert "team" not in result
        assert "manager" not in result

    def test_handles_single_key_in_config(self, mock_unique_ai):
        """Test filtering with a single key in config"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = ["department"]
        mock_unique_ai._event.payload.user_metadata = {
            "department": "Engineering",
            "role": "Developer",
        }

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {"department": "Engineering"}
        assert isinstance(result["department"], str)

    def test_handles_string_values(self, mock_unique_ai):
        """Test that string values in user_metadata are preserved"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = [
            "name",
            "email",
            "department",
            "title",
        ]
        mock_unique_ai._event.payload.user_metadata = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "department": "Engineering",
            "title": "Senior Developer",
            "ignored": "This should not appear",
        }

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "department": "Engineering",
            "title": "Senior Developer",
        }
        assert "ignored" not in result
        # Verify all values are strings
        assert all(isinstance(v, str) for v in result.values())

    def test_handles_empty_dict_user_metadata(self, mock_unique_ai):
        """Test behavior when user_metadata is an empty dict"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = ["department"]
        mock_unique_ai._event.payload.user_metadata = {}

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {}

    def test_handles_empty_string_values(self, mock_unique_ai):
        """Test that empty string values in user_metadata are preserved if key is in config"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = [
            "department",
            "role",
        ]
        mock_unique_ai._event.payload.user_metadata = {
            "department": "Engineering",
            "role": "",
        }

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {"department": "Engineering", "role": ""}
        assert isinstance(result["role"], str)

    def test_preserves_original_metadata_unchanged(self, mock_unique_ai):
        """Test that the original user_metadata dict is not modified"""
        original_metadata = {
            "department": "Engineering",
            "role": "Developer",
            "location": "San Francisco",
        }
        mock_unique_ai._config.agent.prompt_config.user_metadata = ["department"]
        mock_unique_ai._event.payload.user_metadata = original_metadata.copy()

        result = mock_unique_ai._get_filtered_user_metadata()

        # Original should still have all keys
        assert mock_unique_ai._event.payload.user_metadata == original_metadata
        # Result should only have filtered key
        assert result == {"department": "Engineering"}

    def test_handles_special_characters_in_values(self, mock_unique_ai):
        """Test that special characters in string values are preserved"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = [
            "description",
            "notes",
        ]
        mock_unique_ai._event.payload.user_metadata = {
            "description": "User with special chars: @#$%^&*()",
            "notes": "Multi-line\ntext\twith\ttabs",
            "other": "excluded",
        }

        result = mock_unique_ai._get_filtered_user_metadata()

        assert result == {
            "description": "User with special chars: @#$%^&*()",
            "notes": "Multi-line\ntext\twith\ttabs",
        }
        assert all(isinstance(v, str) for v in result.values())

    def test_return_type_is_dict_str_str(self, mock_unique_ai):
        """Test that return type is dict[str, str]"""
        mock_unique_ai._config.agent.prompt_config.user_metadata = [
            "department",
            "role",
        ]
        mock_unique_ai._event.payload.user_metadata = {
            "department": "Engineering",
            "role": "Developer",
        }

        result = mock_unique_ai._get_filtered_user_metadata()

        # Check it's a dict
        assert isinstance(result, dict)
        # Check all keys are strings
        assert all(isinstance(k, str) for k in result.keys())
        # Check all values are strings
        assert all(isinstance(v, str) for v in result.values())
