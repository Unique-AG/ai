import unittest

from unique_toolkit.language_model.utils import (
    convert_string_to_json,
    find_last_json_object,
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
