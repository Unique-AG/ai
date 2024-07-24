import json as j
import re


def convert_string_to_json(string: str):
    """
    Removes any json tags and converts string to json.

    Args:
        string: The string to convert to json.
    
    Returns:
        dict: The json object.

    Raises:
        ValueError: If the string cannot be converted to json.
    """
    cleaned_result = find_last_json_object(string)
    if not cleaned_result:
        raise ValueError("Could not find a valid json object in the string.")
    try:
        json = j.loads(cleaned_result)
    except j.JSONDecodeError:
        raise ValueError("Could not convert the string to JSON.")
    return json


def find_last_json_object(text: str) -> str | None:
    """
    Finds the last json object in a string.
    
    Args:
        text: The text to search for the last json object.
    
    Returns:
        str | None: The last json object as a string or None if no json object was found.
    """

    pattern = r'\{(?:[^{}]|\{[^{}]*\})*\}'
    matches = re.findall(pattern, text)
    if matches:
        return matches[-1]
    else:
        return None