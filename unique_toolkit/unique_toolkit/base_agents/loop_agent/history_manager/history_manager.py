from logging import Logger

from pydantic import BaseModel, Field
from unique_toolkit.unique_toolkit.base_agents.loop_agent.history_manager.utils import transform_chunks_to_string
from unique_toolkit.unique_toolkit.language_model.schemas import LanguageModelAssistantMessage, LanguageModelFunction, LanguageModelMessage, LanguageModelToolMessage
from unique_toolkit.unique_toolkit.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.unique_toolkit.tools.tool import Tool
from unique_toolkit.unique_toolkit.tools.tool_manager import ToolManager


class HistoryManagerConfig (BaseModel):

    class ExperimentalFeatures (BaseModel):
        def __init__(self, full_sources_serialize_dump: bool = False):
            self.full_sources_serialize_dump = full_sources_serialize_dump

        full_sources_serialize_dump: bool = Field(
            default=False,
            description="If True, the sources will be serialized in full, otherwise only the content will be serialized.",
        )
    
    def __init__(self, full_sources_serialize_dump: bool = False):
        self.experimental_features = HistoryManagerConfig.ExperimentalFeatures(
            full_sources_serialize_dump=full_sources_serialize_dump
        )

class HistoryManager:
    _tool_call_result_history: list[ToolCallResponse] = []
    _loop_history: list[LanguageModelMessage] = []
    _source_enumerator = 0
    
    def __init__(
        self,
        logger: Logger,
        config: HistoryManagerConfig,
      ):
        self.config = config
        self.logger = logger




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

        tool_call_result_for_history = (
            self._get_tool_call_result_for_loop_history(
                tool_response=tool_response
            )
        )
        self._loop_history.append(tool_call_result_for_history)
          

    def _get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
    ) -> LanguageModelMessage:

        self.logger.debug(
            f"Appending tool call result to history: {tool_response.name}"
        )
        
        content_chunks = tool_response.content_chunks or [] # it can be that the tool response does not have content chunks

        # Transform content chunks into sources to be appended to tool result
        sources = transform_chunks_to_string(
            content_chunks,
            self._source_enumerator,
            None,  # Use None for SourceFormatConfig
            self.config.experimental_features.full_sources_serialize_dump,
        )
        
        self._source_enumerator += len(sources) # To make sure all sources have unique source numbers

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
            LanguageModelAssistantMessage.from_functions(
                tool_calls=tool_calls
            )
        )

    def add_assistant_message(
        self, message: LanguageModelAssistantMessage
    ) -> None:
        self._loop_history.append(message)