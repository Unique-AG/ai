## 🧭 Overview

This document explains how the Tool Manager organizes, exposes, and executes tools for an LLM-based orchestrator. Code for each capability is embedded in the relevant sections, so you can see how it’s implemented where it matters.

Key capabilities:
- Load and filter tools from configuration and the users choices
- Respects Tool exclusivity, weather it is enabled by the admin or weather the user choose the tool as a must (forced tools)
- Expose tool definitions and prompt enhancements for the LLM
- Detects if a tool requests a handoff so it “takes control”  (e.g., deep research)
- Execute selected tools in parallel with tool-call deduplication and max-call limits
- it returns the ToolCallResponses of all the tools to the orchestrator for further rounds with the LLM and additional processing like preparation for referencing or collection of debug info.


## 🚀 **Initialization and Tool Loading**

The **Tool Manager** is responsible for initializing and managing the tools available to the agent. It supports "Internal"-tools but also both **MCP tools** and **A2A sub-agents**, treating them as tools that can be called directly. Here's a 
breakdown of its functionality:

### **Internal Tools**
Internal tools are loaded directly in the python code. Like the web-search tool or the internal-search tool.

### **Agent-to-Agent Protocol (A2A)**
The A2A protocol enables communication between agents. During initialization, the Tool Manager:
1. Loads all sub-agents defined for the A2A (Agent to Agent) protocol.
2. These sub-agents are treated as callable tools, making them callable by the LLM.

### **MCP Tools**
The Tool Manager also integrates **MCP tools**, which are added to the pool of available tools. These tools can be invoked directly, just like sub-agents, and are managed by the **MCP Manager**.

### **Tool Discovery and Filtering**
The Tool Manager combines tools from three sources:
1. **Internal tools**: Built from the configuration provided by the admin.
2. **MCP tools**: Retrieved from the MCP Manager.
3. **A2A sub-agents**: Loaded via the A2A Manager.

After combining these tools, the manager applies several filters:
- **Exclusivity**: If a tool is marked as exclusive, only that tool is loaded. When a tool is exclusive only that tool can be executed no other (e.g. Deep-research).
- **Enablement**: Disabled tools are excluded. This is done by the admin of the Space to say which ones are available.
- **User Preferences**: Should tools be selected by the end-user in the frontend, they are set as exclusive tools for the first iteration with the model. Then only these can be chosen.

### **Configuration**
The available tools (MCP, sub-agents, and internal tools) are derived directly from the front-end configuration, which is set up by the admin of the space.

---

### **Code Implementation**

#### **Constructor and Initialization**
The constructor initializes the Tool Manager with the necessary runtime context and managers:

<!-- open-source -->
::: unique_toolkit.agentic.tools.tool_manager.ToolManager
    options:
      show_root_heading: false
      show_root_toc_entry: false
      show_root_full_path: false
      show_root_members_full_path: false
      heading_level: 1
      show_source: true



#### **Tool Initialization**
The `_init__tools` method discovers and filters tools:

<!-- open-source -->
::: unique_toolkit.agentic.tools.tool_manager.ToolManager._init__tools
    options:
      show_root_heading: false
      show_root_toc_entry: false
      show_root_full_path: false
      show_root_members_full_path: false
      heading_level: 1
      show_source: true

---

## 📣 Exposing Tools to the Orchestrator and LLM

The orchestrator that works with the tool-manager needs three kinds of information:
- The actual tool objects (for runtime operations)
- Tool “definitions” or schemas consumable by the LLM
- Additional tool-specific prompt enhancements/guidance to help the LLM format call the correct tool and format the output of the tools correctly.

Get loaded tools and log them:
<!-- open-source -->
::: unique_toolkit.agentic.tools.tool_manager.ToolManager.log_loaded_tools
    options:
      show_root_heading: false
      show_source: true

<!-- open-source -->
::: unique_toolkit.agentic.tools.tool_manager.ToolManager.get_tools
    options:
      show_root_heading: false  
      show_source: true

<!-- open-source -->
::: unique_toolkit.agentic.tools.tool_manager.ToolManager.get_tool_by_name
    options:
      show_root_heading: false
      show_source: true

Expose tool definitions and prompts (prompt enhancements):
```python
def get_tool_definitions(
    self,
) -> list[LanguageModelTool | LanguageModelToolDescription]:
    return [tool.tool_description() for tool in self._tools]

def get_tool_prompts(self) -> list[ToolPrompts]:
    return [tool.get_tool_prompts() for tool in self._tools]
```

Evaluation metrics aggregation:
```python
def get_evaluation_check_list(self) -> list[EvaluationMetricName]:
    return list(self._tool_evaluation_check_list)
```


## 🎛️ Forced Tools and Admin/User Constraints

Users can force a subset of tools via the UI. Forced tools are surfaced in an LLM API-compatible structure. So that the orchestrator can hand this information over to the LLM call in the correct format.

Retrieve forced tools and add a forced tool programmatically:
```python
def get_forced_tools(self) -> list[dict[str, Any]]:
    return [
        self._convert_to_forced_tool(t.name)
        for t in self._tools
        if t.name in self._tool_choices
    ]

def add_forced_tool(self, name):
    tool = self.get_tool_by_name(name)
    if not tool:
        raise ValueError(f"Tool {name} not found")
    self._tools.append(tool)
    self._tool_choices.append(tool.name)

def _convert_to_forced_tool(self, tool_name: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {"name": tool_name},
    }
```


## 🧠 Control-Taking Tools (e.g., Deep Research)

Some tools request a handover from the main orchestrator so they can “take control” of the session. The orchestrator can check this before deciding weather to yield control or to continue its flow.

Check if any selected call belongs to a control-taking tool:
```python
def does_a_tool_take_control(self, tool_calls: list[LanguageModelFunction]) -> bool:
    for tool_call in tool_calls:
        tool_instance = self.get_tool_by_name(tool_call.name)
        if tool_instance and tool_instance.takes_control():
            return True
    return False
```


## ⚙️ Tool Execution Workflow

The orchestrator receives the information from the LLM on what tools to be executed in oder for the llm to receive the requested information.
The Tool Manager handles the execution of selected tools with the following steps:

1. **Deduplication**: It removes duplicate tool calls from the LLM, ensuring identical calls (e.g., same tool with identical parameters) are executed only once. This prevents redundant processing caused by occasional LLM errors.

2. **Call Limit Enforcement**: A maximum of two tool calls is allowed per execution round. This prevents overloading the system with excessive requests.

3. **Parallel Execution**: Tools are executed concurrently to save time, as individual tool calls can be time-intensive.

4. **Result Handling**: Once the tools return their responses, the Tool Manager:
   - Sends the results back to the orchestrator.
   - Updates the call history.
   - Extracts references and debug information for further use.

This streamlined process ensures efficient, accurate, and manageable tool execution.",
```python
async def execute_selected_tools(
    self,
    tool_calls: list[LanguageModelFunction],
) -> list[ToolCallResponse]:
    tool_calls = tool_calls

    tool_calls = self.filter_duplicate_tool_calls(
        tool_calls=tool_calls,
    )
    num_tool_calls = len(tool_calls)

    if num_tool_calls > self._config.max_tool_calls:
        self._logger.warning(
            (
                "Number of tool calls %s exceeds the allowed maximum of %s."
                "The tool calls will be reduced to the first %s."
            ),
            num_tool_calls,
            self._config.max_tool_calls,
            self._config.max_tool_calls,
        )
        tool_calls = tool_calls[: self._config.max_tool_calls]

    tool_call_responses = await self._execute_parallelized(
        tool_calls=tool_calls, loop_iteration=loop_iteration)
    return tool_call_responses
```

Parallel execution strategy:
```python
async def _execute_parallelized(
    self,
    tool_calls: list[LanguageModelFunction],
) -> list[ToolCallResponse]:
    self._logger.info("Execute tool calls")

    task_executor = SafeTaskExecutor(
        logger=self._logger,
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
        unpacked_tool_call_result = self._create_tool_call_response(
            result, tool_calls[i]
        )
        tool_call_results_unpacked.append(unpacked_tool_call_result)

    return tool_call_results_unpacked
```

Execute a single tool call:
```python
async def execute_tool_call(
    self, tool_call: LanguageModelFunction
) -> ToolCallResponse:
    self._logger.info(f"Processing tool call: {tool_call.name}")

    tool_instance = self.get_tool_by_name(
        tool_call.name
    )  # we need to copy this as it will have problematic interference on multi calls.

    if tool_instance:
        # Execute the tool
        tool_response: ToolCallResponse = await tool_instance.run(
            tool_call=tool_call
        )
        evaluation_checks = tool_instance.evaluation_check_list()
        self._tool_evaluation_check_list.update(evaluation_checks)

        return tool_response

    return ToolCallResponse(
        id=tool_call.id,  # type: ignore
        name=tool_call.name,
        error_message=f"Tool of name {tool_call.name} not found",
    )
```

Normalize outcomes from the task executor:
```python
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
```


## 🔁 Deduplication and Safety

Before executing, the Tool Manager removes duplicate calls with identical names and arguments to prevent repeated work in the same round.

Deduplicate calls and warn when filtered:
```python
def filter_duplicate_tool_calls(
    self,
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
        self._logger = getLogger(__name__)
        self._logger.warning(
            f"Filtered out {len(tool_calls) - len(unique_tool_calls)} duplicate tool calls."
        )
    return unique_tool_calls
```


## 🗣️ Enhanced Prompting Guidance for the LLM

To optimize tool selection and minimize formatting errors, the orchestrator should:

1. **Incorporate Tool Definitions**  
   - Use `get_tool_definitions()` to retrieve the function/tool schema and provide it to the LLM. This ensures the LLM understands the available tools and their parameters.

2. **Enhance System Prompts with Tool-Specific Guidance**  
   - Inject `get_tool_prompts()` content into the system prompt to:  
     - Clearly define when each tool should be used.  
     - Specify the expected inputs and outputs.  
     - Include argument formatting examples for clarity.

3. **Iterative Feedback for Improved Formatting**  
   - In subsequent interactions, provide explicit formatting guidance based on the tools previously selected. This iterative refinement ensures consistent and accurate tool usage.

### Key Mechanism:  
The orchestrator retrieves both tool definitions and tool prompts. Tool definitions describe the functionality and parameters of each tool, while tool prompts act as enhancements to the system message. These prompts guide the LLM in selecting the correct tool and formatting its arguments effectively. This process improves robustness, ensures accurate tool selection, and enhances the overall response quality.
