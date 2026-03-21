from typing import Any

from unique_sdk.api_resources._chat_completion import ChatCompletion
from unique_sdk.api_resources._integrated import Integrated

from .._base import BaseManager, DomainObject


# ---------------------------------------------------------------------------
# ChatCompletion  (OpenAI-compatible proxy)
# ---------------------------------------------------------------------------


class ChatCompletionResult(DomainObject):
    """An OpenAI-compatible chat completion response."""


class ChatCompletionManager(BaseManager):
    """Generate chat completions via the Unique OpenAI-compatible gateway."""

    async def create(self, **params: Any) -> ChatCompletionResult:
        result = await ChatCompletion.create_async(
            self._company_id, self._user_id, **params
        )
        return ChatCompletionResult(self._user_id, self._company_id, result)


# ---------------------------------------------------------------------------
# Integrated  (Unique's native streaming LLM API)
# ---------------------------------------------------------------------------


class StreamCompletionResult(DomainObject):
    """Result of a streaming chat completion via the Integrated API."""


class ResponsesStreamResult(DomainObject):
    """Result of a responses-stream call via the Integrated API."""


class IntegratedManager(BaseManager):
    """Unified streaming LLM access with search context."""

    async def chat_stream_completion(self, **params: Any) -> StreamCompletionResult:
        result = await Integrated.chat_stream_completion_async(
            self._user_id, self._company_id, **params
        )
        return StreamCompletionResult(self._user_id, self._company_id, result)

    async def responses_stream(self, **params: Any) -> ResponsesStreamResult:
        result = await Integrated.responses_stream_async(
            self._user_id, self._company_id, **params
        )
        return ResponsesStreamResult(self._user_id, self._company_id, result)
