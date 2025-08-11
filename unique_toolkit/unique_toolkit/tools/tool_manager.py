import asyncio
from logging import Logger, getLogger
from pydantic import BaseModel, Field
from unique_toolkit.unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.unique_toolkit.language_model.schemas import LanguageModelFunction, LanguageModelStreamResponse, LanguageModelToolDescription
from unique_toolkit.unique_toolkit.tools.config import ToolBuildConfig
from unique_toolkit.unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.unique_toolkit.tools.schemas import ToolCallResponse, ToolPrompts
from unique_toolkit.unique_toolkit.tools.tool import Tool
from unique_toolkit.unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.unique_toolkit.tools.utils.execution.execution import Result, SafeTaskExecutor


class ForcedToolOption:
   type: str = "function"
   def __init__(self, name: str):
      self.name = name
   

class ToolManagerConfig(BaseModel):
  tools: list[ToolBuildConfig] = Field(
        default=[],
        description="List of tools that the agent can use.",
    )

  max_tool_calls: int = Field(
        default=10,
        ge=1,
        description="Maximum number of tool calls that can be executed in one iteration.",
    )

  def __init__(self, tools: list[ToolBuildConfig], max_tool_calls: int = 10):
    self.tools = tools
    self.max_tool_calls = max_tool_calls


class ToolManager:
  def __init__(
        self,
        logger: Logger,
        config: ToolManagerConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter,
  ):
    
    self.logger = logger
    self.config = config
    self.event = event
    self.tool_progress_reporter = tool_progress_reporter
    self.tools = []
    self.__init__tools()

    
  def __init__tools(self) -> None:
    tool_choices = self.event.payload.tool_choices
    tool_configs = self.config.tools
    self.logger.info("Initializing tool definitions...")
    self.logger.info(f"Tool choices: {tool_choices}")
    self.logger.info(f"Tool configs: {tool_configs}")

    self.available_tools = [ ToolFactory.build_tool_with_settings(
      t.name,
      t,
      t.configuration,
      self.event,
      tool_progress_reporter=self.tool_progress_reporter,

      ) for t in tool_configs]
   
  
    for t in self.available_tools:
        if t.is_exclusive():
            self.tools = [t]
            return
        if not t.is_enabled():
            continue
        if t.name in self.event.payload.disabled_tools:
            continue
        if len(tool_choices) > 0 and t.name not in tool_choices:
            continue

        self.tools.append(t)

  def log_loaded_tools(self):
    self.logger.info(f"Loaded tools: {[tool.name for tool in self.tools]}")


  def get_tools(self) -> list[Tool]:
    return self.tools
 
  def get_tool_by_name(self, name: str) -> Tool | None:
    for tool in self.tools:
      if tool.name == name:
        return tool
    return None
  

  def get_forced_tools(self) -> list[ForcedToolOption]:

    tool_choices = self.event.payload.tool_choices
    return [
          ForcedToolOption(t.name)
          for t in self.tools if t.name in tool_choices
        ]
  
  def get_tool_definitions(self) -> list[LanguageModelToolDescription]:
    return [tool.tool_description() for tool in self.tools]
  
  def get_tool_prompts(self) -> list[ToolPrompts]:
    return [tool.get_tool_prompts() for tool in self.tools]
  
  
  async def execute_selected_tools(
        self,
        tool_calls: list[LanguageModelFunction],
    )  -> list[ToolCallResponse]:
        tool_calls = tool_calls

        tool_calls = self.filter_duplicate_tool_calls(
            tool_calls=tool_calls,
        )
        num_tool_calls = len(tool_calls)
  
        if num_tool_calls > self.config.max_tool_calls:
            self.logger.warning(
                (
                    "Number of tool calls %s exceeds the allowed maximum of %s."
                    "The tool calls will be reduced to the first %s."
                ),
                num_tool_calls,
                self.config.max_tool_calls,
                self.config.max_tool_calls,
            )
            tool_calls = tool_calls[: self.config.max_tool_calls]
      
        tool_call_responses = await self._execute_parallelized(
            tool_calls=tool_calls
        )
        return tool_call_responses


  async def _execute_parallelized(
        self,
        tool_calls: list[LanguageModelFunction],
    ) ->  list[ToolCallResponse]:
        self.logger.info("Execute tool calls")

        task_executor = SafeTaskExecutor(
            logger=self.logger,
        )

        # Create tasks for each tool call
        tasks = [
            task_executor.execute_async(
                self.execute_tool_call,
                tool_call=tool_call,
            )
            for tool_call in tool_calls
        ]

        # Wait until all tasks are finished
        tool_call_results = await asyncio.gather(*tasks)
        tool_call_results_unpacked: list[ToolCallResponse] = []
        for i, result in enumerate(tool_call_results):
          unpacked_tool_call_result = self._create_tool_call_response(result, tool_calls[i])
          tool_call_results_unpacked.append(unpacked_tool_call_result)
        
        return tool_call_results_unpacked

  async def execute_tool_call(
        self, tool_call: LanguageModelFunction
    ) -> ToolCallResponse:
      
        self.logger.info(f"Processing tool call: {tool_call.name}")

        tool_instance = self.get_tool_by_name(tool_call.name)

        if tool_instance:
            # Execute the tool
            tool_response: ToolCallResponse = await tool_instance.run(
                tool_call=tool_call
            )
            return tool_response

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=tool_call.name,
            error_message=f"Tool of name {tool_call.name} not found",
        )
  

  def _create_tool_call_response(
        self, result: Result[ToolCallResponse], tool_call: LanguageModelFunction
    ) -> ToolCallResponse:
      if not result.success:
        return ToolCallResponse(
          id=tool_call.id or "unknown_id",
          name=tool_call.name,
          error_message=str(result.exception),
        )
      unpacked = result.unpack()
      if not isinstance(unpacked, ToolCallResponse):
        return ToolCallResponse(
            id=tool_call.id or "unknown_id",
            name=tool_call.name,
            error_message="Tool call response is not of type ToolCallResponse",
        )
      return unpacked
      
  
  def filter_duplicate_tool_calls(
      self,
      tool_calls: list[LanguageModelFunction],
  ) -> list[LanguageModelFunction]:
      """
      Filter out duplicate tool calls based on name and arguments.
      """

      unique_tool_calls = []

      for call in tool_calls:
          if all(
              not call.equals(other_call)
              for other_call in unique_tool_calls
          ):
              unique_tool_calls.append(call)
        
      if(len(tool_calls) != len(unique_tool_calls)):
          self.logger = getLogger(__name__)
          self.logger.warning(
              f"Filtered out {len(tool_calls) - len(unique_tool_calls)} duplicate tool calls."
          )
      return unique_tool_calls