import json
from typing import Any, Dict

import unique_sdk
from pydantic import BaseModel, Field, create_model

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app.schemas import ChatEvent, McpServer, McpTool
from unique_toolkit.language_model import LanguageModelMessage
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class MCPToolWrapper(Tool[MCPToolConfig]):
    """Wrapper class for MCP tools that implements the Tool interface"""

    def __init__(
        self,
        mcp_server: McpServer,
        mcp_tool: McpTool,
        config: MCPToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ):
        self.name = mcp_tool.name
        super().__init__(config, event, tool_progress_reporter)
        self._mcp_tool = mcp_tool
        self._mcp_server = mcp_server

    def tool_description(self) -> LanguageModelToolDescription:
        """Convert MCP tool schema to LanguageModelToolDescription"""
        # Create a Pydantic model from the MCP tool's input schema
        parameters_model = self._create_parameters_model()

        return LanguageModelToolDescription(
            name=self.name,
            description=self._mcp_tool.description or "",
            parameters=parameters_model,
        )

    def _create_parameters_model(self) -> type[BaseModel]:
        """Create a Pydantic model from MCP tool's input schema"""
        properties = self._mcp_tool.input_schema.get("properties", {})
        required_fields = self._mcp_tool.input_schema.get("required", [])

        # Convert JSON schema properties to Pydantic fields
        fields = {}
        for prop_name, prop_schema in properties.items():
            field_type = self._json_schema_to_python_type(prop_schema)
            field_description = prop_schema.get("description", "")

            if prop_name in required_fields:
                fields[prop_name] = (
                    field_type,
                    Field(description=field_description),
                )
            else:
                fields[prop_name] = (
                    field_type,
                    Field(default=None, description=field_description),
                )

        # Create dynamic model
        return create_model(f"{self.name}Parameters", **fields)

    def _json_schema_to_python_type(self, schema: Dict[str, Any]) -> type:
        """Convert JSON schema type to Python type"""
        json_type = schema.get("type", "string")

        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        return type_mapping.get(json_type, str)

    def tool_description_for_system_prompt(self) -> str:
        """Return tool description for system prompt"""
        # Not using jinja here to keep it simple and not import new packages.
        description = (
            f"**MCP Server**: {self._mcp_server.name}\n"
            f"**Tool Name**: {self.name}\n"
            f"{self._mcp_tool.system_prompt}"
        )

        return description

    def tool_description_for_user_prompt(self) -> str:
        return self._mcp_tool.user_prompt or ""

    def tool_format_information_for_user_prompt(self) -> str:
        return ""

    def tool_format_information_for_system_prompt(self) -> str:
        """Return formatting information for system prompt"""
        return ""  # this is empty for now as it requires to add this to the MCP model of the backend.

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        """Return evaluation check list - empty for MCP tools for now"""
        # TODO: this is empty for now as it requires a setting in the backend for choosing a suitable validator.
        return []

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        """Return evaluation checks based on tool response"""
        return []

    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
    ) -> LanguageModelMessage:
        raise NotImplementedError("function is not supported")

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        """Execute the MCP tool using SDK to call public API"""
        self.logger.info(f"Running MCP tool: {self.name}")

        # Notify progress if reporter is available
        if self._tool_progress_reporter:
            await self._tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=f"**{self.display_name()}**",
                message=f"Executing MCP tool: {self.display_name()}",
                state=ProgressState.RUNNING,
            )

        try:
            # Robust argument extraction and validation
            arguments = self._extract_and_validate_arguments(tool_call)

            # Use SDK to call the public API
            result = await self._call_mcp_tool_via_sdk(arguments)

            # Create successful response
            tool_response = ToolCallResponse(  # TODO: Why result here not applied directly to the body of the tool_response? like so how does it know the results in the history?
                id=tool_call.id or "",
                name=self.name,
                debug_info={
                    "mcp_tool": self.name,
                    "arguments": arguments,
                },
                error_message="",
                content=json.dumps(result),
            )

            # Notify completion
            if self._tool_progress_reporter:
                await self._tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=f"**{self.display_name()}**",
                    message=f"MCP tool completed: {self.display_name()}",
                    state=ProgressState.FINISHED,
                )

            return tool_response

        except Exception as e:
            self.logger.error(f"Error executing MCP tool {self.name}: {e}")

            # Notify failure
            if self._tool_progress_reporter:
                await self._tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=f"**{self.display_name()}**",
                    message=f"MCP tool failed: {str(e)}",
                    state=ProgressState.FAILED,
                )

            return ToolCallResponse(
                id=tool_call.id or "",
                name=self.name,
                debug_info={
                    "mcp_tool": self.name,
                    "error": str(e),
                    "original_arguments": getattr(tool_call, "arguments", None),
                },
                error_message=str(e),
            )

    def _extract_and_validate_arguments(
        self, tool_call: LanguageModelFunction
    ) -> Dict[str, Any]:
        """
        Extract and validate arguments from tool call, handling various formats robustly.

        The arguments field can come in different formats:
        1. As a JSON string (expected format from OpenAI API)
        2. As a dictionary (from internal processing)
        3. As None or empty (edge cases)
        """
        raw_arguments = tool_call.arguments

        # Handle None or empty arguments
        if not raw_arguments:
            self.logger.warning(f"MCP tool {self.name} called with empty arguments")
            return {}

        # Handle string arguments (JSON format)
        if isinstance(raw_arguments, str):
            try:
                parsed_arguments = json.loads(raw_arguments)
                if not isinstance(parsed_arguments, dict):
                    self.logger.warning(
                        f"MCP tool {self.name}: arguments JSON parsed to non-dict: {type(parsed_arguments)}"
                    )
                    return {}
                return parsed_arguments
            except json.JSONDecodeError as e:
                self.logger.error(
                    f"MCP tool {self.name}: failed to parse arguments JSON '{raw_arguments}': {e}"
                )
                raise ValueError(
                    f"Invalid JSON arguments for MCP tool {self.name}: {e}"
                )

        # Handle dictionary arguments (already parsed)
        if isinstance(raw_arguments, dict):
            self.logger.debug(f"MCP tool {self.name}: arguments already in dict format")
            return raw_arguments

        # Handle unexpected argument types
        self.logger.error(
            f"MCP tool {self.name}: unexpected arguments type {type(raw_arguments)}: {raw_arguments}"
        )
        raise ValueError(
            f"Unexpected arguments type for MCP tool {self.name}: {type(raw_arguments)}"
        )

    async def _call_mcp_tool_via_sdk(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool via SDK to public API"""
        try:
            result = unique_sdk.MCP.call_tool(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                name=self.name,
                arguments=arguments,
            )

            self.logger.info(
                f"Calling MCP tool {self.name} with arguments: {arguments}"
            )
            self.logger.debug(f"Result: {result}")

            return result
        except Exception as e:
            self.logger.error(f"SDK call failed for MCP tool {self.name}: {e}")
            raise
