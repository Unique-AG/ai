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

    pattern = r"\{(?:[^{}]|\{[^{}]*\})*\}"
    matches = re.findall(pattern, text)
    if matches:
        return matches[-1]
    else:
        return None


def format_message(user: str, message: str, num_tabs: int = 1) -> str:
    """
    Formats a message from a user by indenting each line with a specified number of tabs.

    Args:
        user (str): The name of the user sending the message.
        message (str): The message content that may include multiple lines.
        num_tabs (int): The number of tabs to use for indenting each line. Default is 1 tab.

    Returns:
        str: A formatted string with user and indented message lines.

    Example:
        >>> format_message("Alice", "Hello\nWorld", 2)
        Alice:
        \t\tHello
        \t\tWorld
    """
    indentation = "\t" * num_tabs
    indented_message = message.replace("\n", "\n" + indentation)
    formatted_message = f"{user}:\n{indentation}{indented_message}"
    return formatted_message
