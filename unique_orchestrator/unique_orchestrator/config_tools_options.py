from typing import Any

from unique_toolkit.app.schemas import ChatEvent


def get_tool_call_option(
    event: ChatEvent,
    active_tool_names: list[str],
) -> list[dict[str, Any]]:
    """Determine which tool to use based on the event.

    Priority:
    1. Tools explicitly mentioned in tool_choices
    2. Tools whose string keys are in the user message

    Returns
    -------
    A list function call dicts.

    """
    # Check tool choices first (higher priority)
    tool_choices = event.payload.tool_choices or []

    return [
        {
            "type": "function",
            "function": {"name": name},
        }
        for name in tool_choices
        if name in active_tool_names
    ]
