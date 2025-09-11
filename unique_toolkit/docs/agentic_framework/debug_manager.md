## 📘 DebugInfoManager Documentation

The `DebugInfoManager` is a service designed to collect, manage, and expose debug information for tools and orchestrators. It provides a centralized key-value store for debug data, ensuring that relevant information is accessible to users with the appropriate roles (e.g., the "Debug" role in the front end).

---

### 🔑 Key Features

1. **Tool Debug Information Extraction**  
   - The `DebugInfoManager` can extract debug data from a list of `ToolCallResponse` objects.  
   - This data is stored under the `"tools"` key, with each tool's name and debug information included.

2. **Direct Debug Data Addition**  
   - Debug information can be added directly to the manager using a key-value pair.  
   - This allows the orchestrator or other services to log additional debug data as needed.

3. **Debug Data Retrieval**  
   - The manager provides a method to retrieve all stored debug information in its current state.

---

### 🛠️ Methods

1. **`extract_tool_debug_info(tool_call_responses: list[ToolCallResponse])`**  
   - Extracts debug information from a list of `ToolCallResponse` objects and appends it to the `"tools"` key in the debug store.

2. **`add(key: str, value: Any)`**  
   - Adds a key-value pair to the debug store, merging it with the existing data.

3. **`get() -> dict`**  
   - Retrieves the current state of the debug information.

---

### 🔄 Code Implementation

```python
class DebugInfoManager:
    def __init__(self):
        self.debug_info = {"tools": []}

    def extract_tool_debug_info(self, tool_call_responses: list[ToolCallResponse]):
        for tool_call_response in tool_call_responses:
            self.debug_info["tools"].append(
                {"name": tool_call_response.name, "data": tool_call_response.debug_info}
            )

    def add(self, key, value):
        self.debug_info = self.debug_info | {key: value}

    def get(self):
        return self.debug_info
```
