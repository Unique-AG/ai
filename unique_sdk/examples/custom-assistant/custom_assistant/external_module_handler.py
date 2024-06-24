from pprint import pprint
from typing import Any, Dict


def handle_module_message(payload: Dict[str, Any], user_id: str, company_id: str):
    info = {
        "name": payload["name"],
        "description": payload["description"],
        "configuration": payload["configuration"],
        "chat_id": payload["chatId"],
        "assistant_id": payload["assistantId"],
        "text": payload["userMessage"]["text"],
        "assistant_message_id": payload["assistantMessage"]["id"],
    }

    print("---External Module Handler---")
    pprint(info)
    print("---END External Module Handler---")
