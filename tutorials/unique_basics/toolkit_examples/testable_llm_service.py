"""Illustrate how you can create a service that is testable.

The language model service can be used for testing and the
chat services can directly be used for the unique frontend.
"""

from pathlib import Path

from utilities_examples.init_sdk import init_from_env_file

from unique_toolkit import ChatService, LanguageModelMessages, LanguageModelService
from unique_toolkit.app import Event
from unique_toolkit.language_model import LanguageModelName
from unique_toolkit.protocols.support import SupportCompleteWithReferences


class MyService:
    def __init__(self, rag_service: SupportCompleteWithReferences):
        self._rag_service = rag_service

    def run(self, messages: LanguageModelMessages):
        # Here you would actually create your messages

        self._rag_service.complete_with_references(
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
        )


company_id, user_id = init_from_env_file(Path(__file__).parent / ".." / ".env")

event = Event.from_json_file(Path("/path/to/event.json"))
llm_service = LanguageModelService(company_id=company_id, user_id=user_id)
chat_service = ChatService(event=event)

my_test_service = MyService(rag_service=llm_service)
my_chat_service = MyService(rag_service=chat_service)
