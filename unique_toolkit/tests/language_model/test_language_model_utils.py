import json
import os
import unittest
from unittest.mock import patch

from unique_toolkit.language_model.utils import (
    LANGUAGE_MODEL_INFOS_ENV_VAR,
    convert_string_to_json,
    find_last_json_object,
    format_message,
    load_language_model_infos_from_env,
)


class TestLanguageModelUtils(unittest.TestCase):
    def test_convert_valid_json(self):
        input_string = '{"name": "John", "age": 30}'
        expected_output = {"name": "John", "age": 30}
        self.assertEqual(convert_string_to_json(input_string), expected_output)

    def test_convert_valid_json_with_extra_text(self):
        input_string = 'Some extra text {"name": "John", "age": 30} more text'
        expected_output = {"name": "John", "age": 30}
        self.assertEqual(convert_string_to_json(input_string), expected_output)

    def test_convert_multiple_json_objects(self):
        input_string = '{"a": 1} {"b": 2} {"c": 3}'
        expected_output = {"c": 3}
        self.assertEqual(convert_string_to_json(input_string), expected_output)

    def test_convert_nested_json(self):
        input_string = '{"outer": {"inner": "value"}}'
        expected_output = {"outer": {"inner": "value"}}
        self.assertEqual(convert_string_to_json(input_string), expected_output)

    def test_convert_invalid_json(self):
        input_string = '{"name": "John", "age": }'
        with self.assertRaises(ValueError):
            convert_string_to_json(input_string)

    def test_convert_no_json(self):
        input_string = "This is just a regular string"
        with self.assertRaises(ValueError):
            convert_string_to_json(input_string)

    def test_find_last_json_object_valid(self):
        input_string = '{"a": 1} {"b": 2}'
        expected_output = '{"b": 2}'
        self.assertEqual(find_last_json_object(input_string), expected_output)

    def test_find_last_json_object_nested(self):
        input_string = '{"outer": {"inner": "value"}}'
        expected_output = '{"outer": {"inner": "value"}}'
        self.assertEqual(find_last_json_object(input_string), expected_output)

    def test_find_last_json_object_no_json(self):
        input_string = "This is just a regular string"
        self.assertIsNone(find_last_json_object(input_string))

    def test_format_message_single_line(self):
        user = "Alice"
        message = "Hello"
        expected_output = "Alice:\n\tHello"
        self.assertEqual(format_message(user, message), expected_output)

    def test_format_message_multi_line(self):
        user = "Bob"
        message = "Hello\nWorld"
        expected_output = "Bob:\n\tHello\n\tWorld"
        self.assertEqual(format_message(user, message), expected_output)

    def test_format_message_with_tabs(self):
        user = "Charlie"
        message = "Line 1\nLine 2"
        expected_output = "Charlie:\n\t\tLine 1\n\t\tLine 2"
        self.assertEqual(format_message(user, message, num_tabs=2), expected_output)


class TestLoadLanguageModelInfosFromEnv(unittest.TestCase):
    def setUp(self):
        # Clear the cache before each test
        load_language_model_infos_from_env.cache_clear()

    def tearDown(self):
        # Clear the cache after each test
        load_language_model_infos_from_env.cache_clear()

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_empty_dict_when_env_not_set(self):
        result = load_language_model_infos_from_env()
        self.assertEqual(result, {})

    @patch.dict(os.environ, {LANGUAGE_MODEL_INFOS_ENV_VAR: ""})
    def test_returns_empty_dict_when_env_is_empty(self):
        result = load_language_model_infos_from_env()
        self.assertEqual(result, {})

    @patch.dict(os.environ, {LANGUAGE_MODEL_INFOS_ENV_VAR: "not valid json"})
    def test_returns_empty_dict_on_invalid_json(self):
        result = load_language_model_infos_from_env()
        self.assertEqual(result, {})

    @patch.dict(os.environ, {LANGUAGE_MODEL_INFOS_ENV_VAR: '["a", "b", "c"]'})
    def test_returns_empty_dict_when_json_is_list(self):
        result = load_language_model_infos_from_env()
        self.assertEqual(result, {})

    @patch.dict(os.environ, {LANGUAGE_MODEL_INFOS_ENV_VAR: '"just a string"'})
    def test_returns_empty_dict_when_json_is_string(self):
        result = load_language_model_infos_from_env()
        self.assertEqual(result, {})

    def test_loads_single_model_info(self):
        model_infos = {
            "AZURE_GPT_4o_CUSTOM": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom",
                "capabilities": ["function_calling", "streaming", "vision"],
                "token_limits": {"token_limit_input": 3000, "token_limit_output": 150},
            }
        }
        with patch.dict(
            os.environ, {LANGUAGE_MODEL_INFOS_ENV_VAR: json.dumps(model_infos)}
        ):
            result = load_language_model_infos_from_env()
            self.assertEqual(result, model_infos)
            self.assertIn("AZURE_GPT_4o_CUSTOM", result)
            self.assertEqual(
                result["AZURE_GPT_4o_CUSTOM"]["name"], "AZURE_GPT_4o_2024_1120"
            )

    def test_loads_multiple_model_infos(self):
        model_infos = {
            "AZURE_GPT_4o_CUSTOM": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom",
                "capabilities": ["function_calling", "streaming", "vision"],
                "token_limits": {"token_limit_input": 3000, "token_limit_output": 150},
            },
            "AZURE_GPT_4o_2024_1120_1234": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom",
                "capabilities": ["function_calling", "streaming", "vision"],
                "token_limits": {"token_limit_input": 3000, "token_limit_output": 150},
            },
        }
        with patch.dict(
            os.environ, {LANGUAGE_MODEL_INFOS_ENV_VAR: json.dumps(model_infos)}
        ):
            result = load_language_model_infos_from_env()
            self.assertEqual(len(result), 2)
            self.assertIn("AZURE_GPT_4o_CUSTOM", result)
            self.assertIn("AZURE_GPT_4o_2024_1120_1234", result)

    def test_skips_invalid_model_info_entries(self):
        model_infos = {
            "VALID_MODEL": {"name": "valid", "provider": "AZURE"},
            "INVALID_MODEL": "not a dict",
        }
        with patch.dict(
            os.environ, {LANGUAGE_MODEL_INFOS_ENV_VAR: json.dumps(model_infos)}
        ):
            result = load_language_model_infos_from_env()
            self.assertEqual(len(result), 1)
            self.assertIn("VALID_MODEL", result)
            self.assertNotIn("INVALID_MODEL", result)

    def test_key_is_used_for_lookup_not_name_field(self):
        # The key in the dict should be used for lookup, not the "name" field inside
        model_infos = {
            "MY_CUSTOM_KEY": {
                "name": "DIFFERENT_NAME",
                "provider": "AZURE",
            }
        }
        with patch.dict(
            os.environ, {LANGUAGE_MODEL_INFOS_ENV_VAR: json.dumps(model_infos)}
        ):
            result = load_language_model_infos_from_env()
            self.assertIn("MY_CUSTOM_KEY", result)
            self.assertNotIn("DIFFERENT_NAME", result)
