import asyncio
import logging
import traceback
from typing import Sequence

from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.utils.execution.execution import (
    Result,
    SafeTaskExecutor,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)

logger = logging.getLogger(__name__)


def filter_duplicate_tool_calls(
    tool_calls: list[LanguageModelFunction],
) -> list[LanguageModelFunction]:
    """
    Filter out duplicate tool calls based on name and arguments.
    """

    unique_tool_calls = []

    for call in tool_calls:
        if all(not call == other_call for other_call in unique_tool_calls):
            unique_tool_calls.append(call)

    if len(tool_calls) != len(unique_tool_calls):
        num_filtered = len(tool_calls) - len(unique_tool_calls)
        logger.warning("Filtered out %s duplicate tool calls.", num_filtered)

    return unique_tool_calls


def _create_tool_call_response_from_result(
    result: Result[ToolCallResponse],
    tool_call: LanguageModelFunction,
    log_exceptions_to_debug_info: bool = True,
) -> ToolCallResponse:
    if not result.success:
        exception = result.exception

        response = ToolCallResponse(
            id=tool_call.id,
            name=tool_call.name,
            error_message=str(result.exception),
        )

        if exception and log_exceptions_to_debug_info:
            response.update_debug_info(
                "error_trace",
                "".join(
                    traceback.format_exception(
                        type(exception), exception, exception.__traceback__
                    )
                ),
            )
        return response

    return result.unpack()


async def _execute_tool_call(
    tool: Tool, tool_call: LanguageModelFunction
) -> ToolCallResponse:
    logger.info("Executing tool: %s", tool.name)

    return await tool.run(tool_call=tool_call)


async def _tool_not_found_result(tool_call: LanguageModelFunction) -> ToolCallResponse:
    return ToolCallResponse(
        id=tool_call.id,
        name=tool_call.name,
        error_message=f"Tool of name {tool_call.name} not found",
    )


async def execute_tools_parallelized(
    tools: Sequence[Tool],
    tool_calls: Sequence[LanguageModelFunction],
    log_exceptions_to_debug_info: bool = True,
) -> list[ToolCallResponse]:
    tools_by_name = {tool.name: tool for tool in tools}

    task_executor = SafeTaskExecutor(
        logger=logger,
    )

    tasks = []
    for tool_call in tool_calls:
        if tool_call.name not in tools_by_name:
            tasks.append(task_executor.execute_async(_tool_not_found_result, tool_call))
        else:
            tasks.append(
                task_executor.execute_async(
                    _execute_tool_call, tools_by_name[tool_call.name], tool_call
                )
            )

    task_results = await asyncio.gather(*tasks)

    return [
        _create_tool_call_response_from_result(
            result, tool_call, log_exceptions_to_debug_info
        )
        for result, tool_call in zip(task_results, tool_calls)
    ]
