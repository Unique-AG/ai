from logging import Logger
from typing import Annotated, Awaitable, Callable

from pydantic import BaseModel, Field

from unique_toolkit.app.schemas import ChatEvent



from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessage,   
    LanguageModelMessages,
    LanguageModelToolMessage
)

from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.history_manager.utils import transform_chunks_to_string

from unique_toolkit._common.validators import LMI
from unique_toolkit.history_manager.loop_token_reducer import LoopTokenReducer
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.tools.config import get_configuration_dict

DeactivatedNone = Annotated[
    None,
    Field(title="Deactivated", description="None"),
]

class UploadedContentConfig(BaseModel):
    model_config = get_configuration_dict()

    user_context_window_limit_warning: str = Field(
        default="The uploaded content is too large to fit into the ai model. "
        "Unique AI will search for relevant sections in the material and if needed combine the data with knowledge base content",
        description="Message to show when using the Internal Search instead of upload and chat tool due to context window limit. Jinja template.",
    )
    percent_for_uploaded_content: float = Field(
        default=0.6,
        ge=0.0,
        lt=1.0,
        description="The fraction of the max input tokens that will be reserved for the uploaded content.",
    )

class ExperimentalFeatures(BaseModel):

    full_sources_serialize_dump: bool = Field(
        default=False,
        description="If True, the sources will be serialized in full, otherwise only the content will be serialized.",
    )


class HistoryManagerConfig(BaseModel):


    experimental_features: ExperimentalFeatures = Field(
        default=ExperimentalFeatures(),
        description="Experimental features for the history manager.",
    )


    percent_of_max_tokens_for_history: float = Field(
        default=0.2,
        ge=0.0,
        lt=1.0,
        description="The fraction of the max input tokens that will be reserved for the history.",
    )

    language_model: LMI = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_1120
    )

    @property
    def max_history_tokens(self) -> int:
        return int(
            self.language_model.token_limits.token_limit_input
            * self.percent_of_max_tokens_for_history,
        )

    uploaded_content_config: (
        Annotated[
            UploadedContentConfig,
            Field(title="Active"),
        ]
        | DeactivatedNone
    ) = UploadedContentConfig()



class HistoryManager:
    """
    Manages the history of tool calls and conversation loops.

    This class is responsible for:
    - Storing and maintaining the history of tool call results and conversation messages.
    - Merging uploaded content with the conversation history for a unified view.
    - Limiting the history to fit within a configurable token window for efficient processing.
    - Providing methods to retrieve, manipulate, and append to the conversation history.
    - Handling post-processing steps to clean or modify the history as needed.

    Key Features:
    - Tool Call History: Tracks the results of tool calls and appends them to the conversation history.
    - Loop History: Maintains a record of conversation loops, including assistant and user messages.
    - History Merging: Combines uploaded files and chat messages into a cohesive history.
    - Token Window Management: Ensures the history stays within a specified token limit for optimal performance.
    - Post-Processing Support: Allows for custom transformations or cleanup of the conversation history.

    The HistoryManager serves as the backbone for managing and retrieving conversation history in a structured and efficient manner.
    """
    _tool_call_result_history: list[ToolCallResponse] = []
    _loop_history: list[LanguageModelMessage] = []
    _source_enumerator = 0

    def __init__(
        self,
        logger: Logger,
        event: ChatEvent,
        config: HistoryManagerConfig,
        language_model: LMI,
        reference_manager: ReferenceManager,
    ):
        self._config = config
        self._logger = logger
        self._language_model = language_model
        self._token_reducer = LoopTokenReducer(
            logger=self._logger,
            event=event,
            max_history_tokens=self._config.max_history_tokens,
            has_uploaded_content_config=bool(self._config.uploaded_content_config),
            language_model=self._language_model,
            reference_manager=reference_manager,
        )


    def has_no_loop_messages(self) -> bool:
        return len(self._loop_history) == 0

    def add_tool_call_results(self, tool_call_results: list[ToolCallResponse]):
        for tool_response in tool_call_results:
            if not tool_response.successful:
                self._loop_history.append(
                    LanguageModelToolMessage(
                        name=tool_response.name,
                        tool_call_id=tool_response.id,
                        content=f"Tool call {tool_response.name} failed with error: {tool_response.error_message}",
                    )
                )
                continue
            self._append_tool_call_result_to_history(tool_response)

    def _append_tool_call_result_to_history(
        self,
        tool_response: ToolCallResponse,
    ) -> None:
        tool_call_result_for_history = self._get_tool_call_result_for_loop_history(
            tool_response=tool_response
        )
        self._loop_history.append(tool_call_result_for_history)

    def _get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
    ) -> LanguageModelMessage:
        self._logger.debug(
            f"Appending tool call result to history: {tool_response.name}"
        )

        content_chunks = (
            tool_response.content_chunks or []
        )  # it can be that the tool response does not have content chunks

        # Transform content chunks into sources to be appended to tool result
        sources = transform_chunks_to_string(
            content_chunks,
            self._source_enumerator,
            None,  # Use None for SourceFormatConfig
            self._config.experimental_features.full_sources_serialize_dump,
        )

        self._source_enumerator += len(
            sources
        )  # To make sure all sources have unique source numbers

        # Append the result to the history
        return LanguageModelToolMessage(
            content=sources,
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )

    def _append_tool_calls_to_history(
        self, tool_calls: list[LanguageModelFunction]
    ) -> None:
        self._loop_history.append(
            LanguageModelAssistantMessage.from_functions(tool_calls=tool_calls)
        )

    def add_assistant_message(self, message: LanguageModelAssistantMessage) -> None:
        self._loop_history.append(message)

        
    async def get_history_for_model_call(
        self,
        original_user_message: str,
        rendered_user_message_string: str,
        rendered_system_message_string: str,
        remove_from_text: Callable[[str], Awaitable[str]]
    ) -> LanguageModelMessages:
        self._logger.info("Getting history for model call -> ")

        messages = await self._token_reducer.get_history_for_model_call(
            original_user_message=original_user_message,
            rendered_user_message_string=rendered_user_message_string,
            rendered_system_message_string=rendered_system_message_string,
            loop_history=self._loop_history,
            remove_from_text=remove_from_text,
        )
        return messages