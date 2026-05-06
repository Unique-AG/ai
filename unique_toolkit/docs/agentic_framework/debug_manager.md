## 📘 DebugInfoManager Documentation

The `DebugInfoManager` is a service designed to collect, manage, and expose debug information for tools and orchestrators. It provides a centralized key-value store for debug data, ensuring that relevant information is accessible to users with the appropriate roles (e.g., the "Debug" role in the front end).

---

### 🔑 Key Features

1. **Tool Debug Information Extraction**  
   - The `DebugInfoManager` can extract debug data from a list of `ToolCallResponse` objects.  
   - This data is stored under the `"tools"` key, with each tool's name and debug information included.

2. **Built-in Tool Debug Information Extraction**  
   - For OpenAI built-in tools (e.g., the Code Interpreter), debug data is extracted directly from a `LanguageModelStreamResponse`.  
   - Duplicate calls within a single stream response are automatically deduplicated by call ID before being appended to the `"tools"` key.

3. **Direct Debug Data Addition**  
   - Debug information can be added directly to the manager using a key-value pair.  
   - This allows the orchestrator or other services to log additional debug data as needed.

4. **Debug Data Retrieval**  
   - The manager provides a method to retrieve all stored debug information in its current state.

---

### 🛠️ Methods

1. **`extract_tool_debug_info(tool_call_responses: list[ToolCallResponse], loop_iteration_index: int | None = None)`**  
   - Extracts debug information from a list of `ToolCallResponse` objects and appends it to the `"tools"` key in the debug store.  
   - When `loop_iteration_index` is provided, it is stored under `"loop_iteration"` inside each tool's `"info"` dict.

2. **`extract_builtin_tool_debug_info(stream_response: LanguageModelStreamResponse, loop_iteration_index: int | None = None)`**  
   - Extracts debug information for OpenAI built-in tools from a `LanguageModelStreamResponse` and appends it to the `"tools"` key.  
   - Only processes `ResponsesLanguageModelStreamResponse` instances; returns without modification for other stream response types.  
   - Deduplicates code interpreter calls by ID so streaming duplicates are never double-counted.  
   - When `loop_iteration_index` is provided, it is stored under `"loop_iteration"` inside each tool's `"info"` dict.

3. **`add(key: str, value: Any)`**  
   - Adds a key-value pair to the debug store, merging it with the existing data.

4. **`get() -> dict`**  
   - Retrieves the current state of the debug information.

---

### 🔄 Code Implementation

```{.python #debug-manager-implementation}
class DebugInfoManager:
    def __init__(self):
        self.debug_info = {"tools": []}

    def extract_tool_debug_info(
        self,
        tool_call_responses: list[ToolCallResponse],
        loop_iteration_index: int | None = None,
    ) -> None:
        for tool_call_response in tool_call_responses:
            debug_info = (
                tool_call_response.debug_info.copy()
                if tool_call_response.debug_info
                else {}
            )
            tool_info: dict = {
                "name": tool_call_response.name,
                "info": debug_info,
            }
            if debug_info.get("mcp_server"):
                tool_info["mcp_server"] = debug_info["mcp_server"]
            if loop_iteration_index is not None:
                tool_info["info"]["loop_iteration"] = loop_iteration_index
            self.debug_info["tools"].append(tool_info)

    def extract_builtin_tool_debug_info(
        self,
        stream_response: LanguageModelStreamResponse,
        loop_iteration_index: int | None = None,
    ) -> None:
        self.debug_info["tools"].extend(
            _extract_tool_calls_from_stream_response(
                stream_response, loop_iteration_index
            )
        )

    def add(self, key: str, value: Any) -> None:
        self.debug_info = self.debug_info | {key: value}

    def get(self) -> dict[str, Any]:
        return self.debug_info
```
