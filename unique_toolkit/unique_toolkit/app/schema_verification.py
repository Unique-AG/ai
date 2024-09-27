import json
from jsonschema import validate, ValidationError
from typing import Any, Dict

def validate_event_payload(event_payload: Dict[str, Any], schema_file_path: str) -> bool:
    """
    Validate the given event payload against a JSON schema.

    Args:
        event_payload (Dict[str, Any]): The event payload to validate. It should match the structure expected by the schema.
        schema_file_path (str): The path to the JSON schema file against which to validate the payload.

    Returns:
        bool: Returns True if the payload is valid, otherwise raises a ValidationError.

    Raises:
        ValidationError: If the payload does not conform to the JSON schema.
    """
    # Load the JSON schema from the provided file path
    with open(schema_file_path, 'r') as schema_file:
        schema = json.load(schema_file)

    # Validate the payload against the schema
    try:
        validate(instance=event_payload, schema=schema)
        print("Payload is valid")
        return True
    except ValidationError as e:
        print(f"Payload is invalid: {e.message}")
        raise

# Example usage
if __name__ == "__main__":
    event_payload = {
        "name": "test",
        "description": "example description",
        "configuration": {},
        "chatId": "chat_123",
        "assistantId": "assistant_456",
        "userMessage": {
            "id": "user_msg_789",
            "text": "hello",
            "createdAt": "2023-09-26T00:00:00Z",
            "language": "en"
        },
        "assistantMessage": {
            "id": "assistant_msg_101",
            "createdAt": "2023-09-26T00:00:00Z"
        }
    }

    # Validate the payload against the schema located at 'scehma.json'
    try:
        validate_event_payload(event_payload, 'schema.json')
    except ValidationError:
        pass
