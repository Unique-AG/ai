import unique_sdk

from unique_toolkit.chat.state import ChatState
from unique_toolkit.performance.async_wrapper import to_async

from .models import LLMModelName


class LLMService:
    def __init__(self, state: ChatState):
        self.state = state

    def stream_complete(
        self,
        *,
        messages: list,
        model_name: LLMModelName,
        search_contexts: list = [],
        debug_info: dict = {},
        timeout: int = 100_000,
        temperature: float = 0.25,
    ):
        """
        Streams a completion in the chat session synchronously.

        Args:
            messages (list): The messages to stream.
            search_contexts (list): The search context.
            model_name (LLMModelName): The language model to use for the completion.
            debug_info (dict): The debug information.
            timeout (int, optional): The timeout value in milliseconds. Defaults to 100_000.
            temperature (float, optional): The temperature value for the completion. Defaults to 0.25.

        Returns:
            A generator yielding streamed completion chunks.
        """
        return self._trigger_stream_complete(
            messages,
            search_contexts,
            model_name.name,
            debug_info,
            timeout,
            temperature,
        )

    @to_async
    def async_stream_complete(
        self,
        *,
        messages: list,
        model_name: LLMModelName,
        search_contexts: list = [],
        debug_info: dict = {},
        timeout: int = 100_000,
        temperature: float = 0.25,
    ):
        """
        Streams a completion in the chat session asynchronously.

        Args:
            messages (list[dict[str, str]]): The messages to stream.
            search_contexts (list): The search context.
            debug_info (dict): The debug information.
            model_name (LLMModelName): The language model to use for the completion.
            timeout (int, optional): The timeout value in milliseconds. Defaults to 100_000.
            temperature (float, optional): The temperature value for the completion. Defaults to 0.25.

        Returns:
            A generator yielding streamed completion chunks.
        """
        return self._trigger_stream_complete(
            messages, search_contexts, model_name, debug_info, timeout, temperature
        )

    def complete(
        self,
        *,
        messages: list,
        model_name: LLMModelName,
        temperature: float = 0,
        timeout: int = 240000,
    ) -> str:
        """
        Calls the completion endpoint synchronously without streaming the response.

        Args:
            messages (list[dict[str, str]]): The messages to complete.
            model_name (LLMModelName): The model name.
            temperature (float, optional): The temperature value. Defaults to 0.
            timeout (int, optional): The timeout value in milliseconds. Defaults to 240000.

        Returns:
            str: The completed message content.
        """
        return self._trigger_complete(messages, model_name, temperature, timeout)

    @to_async
    def async_complete(
        self,
        *,
        messages: list,
        model_name: LLMModelName,
        temperature: float = 0,
        timeout: int = 240000,
    ) -> str:
        """
        Calls the completion endpoint asynchronously without streaming the response.

        Args:
            messages (list[dict[str, str]]): The messages to complete.
            model_name (LLMModelName): The model name.
            temperature (float, optional): The temperature value. Defaults to 0.
            timeout (int, optional): The timeout value in milliseconds. Defaults to 240000.

        Returns:
            str: The completed message content.
        """
        return self._trigger_complete(
            messages,
            model_name.name,
            temperature,
            timeout,
        )

    def _trigger_stream_complete(
        self,
        messages: list,
        search_contexts: list,
        model_name: str,
        debug_info: dict,
        timeout: int,
        temperature: float,
    ):
        return unique_sdk.Integrated.chat_stream_completion(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            assistantMessageId=self.state.assistant_message_id,
            userMessageId=self.state.user_message_id,
            messages=messages,
            chatId=self.state.chat_id,
            searchContext=search_contexts,
            debugInfo=debug_info,
            model=model_name,  # type: ignore
            timeout=timeout,
            temperature=temperature,
            assistantId=self.state.assistant_id,
        )

    def _trigger_complete(
        self,
        messages: list,
        model_name: str,
        temperature: float,
        timeout: int,
    ) -> str:
        result = unique_sdk.ChatCompletion.create(
            company_id=self.state.company_id,
            model=model_name,  # type: ignore
            messages=messages,
            timeout=timeout,
            temperature=temperature,
        )
        return result.choices[-1]["message"]["content"]
