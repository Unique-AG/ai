import asyncio
from abc import ABC
from logging import Logger

from unique_toolkit.agentic.tools.utils.execution.execution import SafeTaskExecutor
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model.schemas import (
    LanguageModelStreamResponse,
    ResponsesLanguageModelStreamResponse,
)


class Postprocessor(ABC):
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name

    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        raise NotImplementedError("Subclasses must implement this method.")

    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        raise NotImplementedError(
            "Subclasses must implement this method to apply post-processing to the response."
        )

    async def remove_from_text(self, text: str) -> str:
        raise NotImplementedError(
            "Subclasses must implement this method to remove post-processing from the message."
        )


class ResponsesApiPostprocessor(ABC):
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name

    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        raise NotImplementedError("Subclasses must implement this method.")

    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        raise NotImplementedError(
            "Subclasses must implement this method to apply post-processing to the response."
        )

    async def remove_from_text(self, text: str) -> str:
        raise NotImplementedError(
            "Subclasses must implement this method to remove post-processing from the message."
        )


class PostprocessorManager:
    """
    Manages and executes postprocessors for modifying and refining responses.

    This class is responsible for:
    - Storing and managing a collection of postprocessor instances.
    - Executing postprocessors asynchronously to refine loop responses.
    - Applying modifications to assistant messages based on postprocessor results.
    - Providing utility methods for text manipulation using postprocessors.

    Key Features:
    - Postprocessor Management: Allows adding and retrieving postprocessor instances.
    - Asynchronous Execution: Runs all postprocessors concurrently for efficiency.
    - Response Modification: Applies postprocessing changes to assistant messages when necessary.
    - Text Cleanup: Supports removing specific patterns or content from text using postprocessors.
    - Error Handling: Logs warnings for any postprocessors that fail during execution.

    The PostprocessorManager serves as a centralized system for managing and applying postprocessing logic to enhance response quality and consistency.
    """

    def __init__(
        self,
        logger: Logger,
        chat_service: ChatService,
    ):
        self._logger = logger
        self._chat_service = chat_service
        self._postprocessors: list[Postprocessor | ResponsesApiPostprocessor] = []

    def add_postprocessor(
        self, postprocessor: Postprocessor | ResponsesApiPostprocessor
    ):
        self._postprocessors.append(postprocessor)

    def get_postprocessors(
        self, name: str
    ) -> list[Postprocessor | ResponsesApiPostprocessor]:
        return self._postprocessors

    async def run_postprocessors(
        self,
        loop_response: LanguageModelStreamResponse,
    ) -> None:
        task_executor = SafeTaskExecutor(
            logger=self._logger,
        )

        if isinstance(loop_response, ResponsesLanguageModelStreamResponse):
            postprocessors = self._postprocessors
        else:
            postprocessors = [
                postprocessor
                for postprocessor in self._postprocessors
                if isinstance(postprocessor, Postprocessor)
            ]

        tasks = [
            task_executor.execute_async(
                self.execute_postprocessors,
                loop_response=loop_response,
                postprocessor_instance=postprocessor,
            )
            for postprocessor in postprocessors
        ]
        postprocessor_results = await asyncio.gather(*tasks)

        for i, result in enumerate(postprocessor_results):
            if not result.success:
                self._logger.warning(
                    f"Postprocessor {self._postprocessors[i].get_name()} failed to run."
                )

        modification_results = [
            postprocessor.apply_postprocessing_to_response(loop_response)  # type: ignore
            for postprocessor in postprocessors
        ]

        has_been_modified = any(modification_results)

        if has_been_modified:
            self._chat_service.modify_assistant_message(
                content=loop_response.message.text,
                message_id=loop_response.message.id,
                references=loop_response.message.references,
            )

    async def execute_postprocessors(
        self,
        loop_response: LanguageModelStreamResponse,
        postprocessor_instance: Postprocessor | ResponsesApiPostprocessor,
    ) -> None:
        await postprocessor_instance.run(loop_response)  # type: ignore

    async def remove_from_text(
        self,
        text: str,
    ) -> str:
        for postprocessor in self._postprocessors:
            text = await postprocessor.remove_from_text(text)
        return text
