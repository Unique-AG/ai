from pprint import pprint
from typing import Any, Dict

from langchain.llms import Ollama

import unique_sdk


def handle_user_message(payload: Dict[str, Any], user_id: str, company_id: str):
    text = payload["text"]
    chat_id = payload["chatId"]
    assistant_id = payload["assistantId"]

    llm = Ollama(model="llama2")
    response = llm.invoke(text)

    response = text

    message = unique_sdk.Message.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        assistantId=assistant_id,
        text=response,
        role="ASSISTANT",
    )

    print("---User Event Handler---")
    pprint(message)
    print("---END User Event Handler---")
