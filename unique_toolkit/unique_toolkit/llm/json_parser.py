import json
import re


def convert_to_json(result: str):
    """
    Removes any json tags and converts string to json.
    """
    cleaned_result = find_last_json_object(result)
    if not cleaned_result:
        raise ValueError("Could not find a valid json object in the result.")
    return json.loads(cleaned_result)


def find_last_json_object(text) -> str | None:
    pattern = r"\{(?:[^{}]|\{[^{}]*\})*\}"
    matches = re.findall(pattern, text)
    if matches:
        return matches[-1]
    else:
        return None
