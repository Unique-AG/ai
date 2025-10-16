from unique_toolkit.protocols.support import ResponsesSupportCompleteWithReferences
from unique_toolkit.services.chat_service import ChatService


class ResponsesStreamingHandler(ResponsesSupportCompleteWithReferences):
    def __init__(self, chat_service: ChatService):
        self._chat_service = chat_service

    def complete_with_references(self, *args, **kwargs):
        return self._chat_service.complete_responses_with_references(*args, **kwargs)

    async def complete_with_references_async(self, *args, **kwargs):
        return await self._chat_service.complete_responses_with_references_async(
            *args, **kwargs
        )
