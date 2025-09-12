## 📘 Tool Class Documentation

This document provides a detailed explanation of the `Tool` class, which serves as an abstract base class for tools used by the Tool Manager in orchestrating interactions with large language models (LLMs). The `Tool` class defines the structure, configuration, and behavior of tools, ensuring consistency and flexibility for developers.

**Every** tool must implement this abstract class. Doing so allows for the Frontend and the Agent-Orchestrator to correctly interact with the tool.


### 📦 Tool-Configuration

The configuration of a tool is a critical component that defines its behavior and settings. Each tool's configuration inherits from the **Base Tool Config**, a Pythonic class that provides a structured and standardized way to define tool-specific settings. This approach ensures seamless integration with the front end and simplifies the process of defining, validating, and using configurations.


#### 🛠️ Configuration Inheritance

**Inherit from Base Tool Config**:  All configurations must extend the `BaseToolConfig` class a pydantic class, which provides the foundational structure for tool settings.

All tool configurations must inherit from the **Base Tool Config**. This inheritance provides the following benefits:

1. **JSON Schema Exposure**:  
   The configuration can be exposed as a JSON schema, making it clear what settings the tool can accept. This schema allows the front end to render the configuration dynamically, ensuring that only valid settings are passed to the tool.

2. **Validation**:  
   By using a structured configuration class, tools avoid receiving raw, unvalidated configurations. This ensures that all settings are properly defined and adhere to the expected format.

3. **Ease of Integration**:  
   The JSON schema simplifies the integration process with the front end, as the schema acts as a contract between the tool and the front end. The configurations can then be rendered in the frontend for simpler setup of agents in the space configuration.

---

### 🏗️ Tool Registration in the Tool Factory

To enable automatic instantiation of tools based on their configuration, each tool must be registered in the **Tool Factory**. This registration links the tool class with its corresponding configuration class, allowing the orchestrator to create tool instances dynamically.

#### Registration Process

1. **Register the Tool**:  
   At the end of the tool's implementation file, register the tool and its configuration with the `ToolFactory`.

   ```python
   ToolFactory.register_tool(InternalSearchTool, InternalSearchConfig)
   ```
   
---

### 🛠️ Overview of the Tool Class

The `Tool` class is the backbone of the Tool Manager, enabling modular and reusable components to execute specific tasks. Each tool is designed to integrate seamlessly with the orchestrator, providing functionality such as searches, user interactions, or other operations requested by LLMs.

The **core functionality** of any tool is defined in its **`run` method**, which executes the tool's primary task. This method is abstract and must be implemented by each tool, making it the most critical part of the class.

---

### 🚀 Key Method: `run`

The **`run` method** is where the actual execution of the tool happens. It is an abstract method that must be implemented by every tool. This method takes a `LanguageModelFunction` as input and returns a `ToolCallResponse`. The `run` method is responsible for performing the tool's specific task, such as executing a search, generating content, or interacting with external systems.

#### Method Signature:
```python
@abstractmethod
async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:

    raise NotImplementedError
```

This method is the heart of the tool's functionality and must be tailored to the specific requirements of the tool being implemented.


### 🧩 Initialization

The `Tool` class is initialized with a configuration object, an event, and an optional progress reporter. These components are essential for setting up the tool and ensuring it operates correctly.

#### Constructor:
```python
def __init__(
    self,
    config: ConfigType,
    event: ChatEvent,
    tool_progress_reporter: ToolProgressReporter | None = None,
):
    self.settings = ToolBuildConfig(
        name=self.name,
        configuration=config,
    )

    self.config = config
    module_name = "default overwrite for module name"
    self.logger = getLogger(f"{module_name}.{__name__}")
    self.debug_info: dict = {}

    # Deprecated properties
    self._event: ChatEvent = event
    self._tool_progress_reporter: ToolProgressReporter | None = (
        tool_progress_reporter
    )
```

#### 🔄 Progress Reporting

Tools can report their progress during execution using the **`tool_progress_reporter`** property. This feature is essential for keeping users informed about the tool's status, especially for long-running operations. For example, a tool might report stages like "Searching...", "Processing results...", or "Preparing output...".

Progress updates are typically sent before any streaming begins, ensuring users are aware of the tool's current state.

---

### 🔑 Tool Identification and Configuration

Each tool is defined by a set of properties that determine its identity, configuration, and behavior. These properties are critical for the orchestrator to understand how and when to use the tool.

#### 1. **Tool Name**
   - **`name`**: The internal, code-oriented name of the tool.
   - **`display_name`**: The user-facing name of the tool.

   ```python
   name: str
   def display_name(self) -> str:
       """The display name of the tool."""
       return self.settings.display_name
   ```

#### 2. **Icon**
   - **`icon`**: A visual representation of the tool, used in user interfaces.

   ```python
   def icon(self) -> str:
       """The icon of the tool."""
       return self.settings.icon
   ```

#### 3. **Exclusivity**
   - **`is_exclusive`**: Indicates whether the tool can run exclusively, meaning no other tools can execute simultaneously.

   ```python
   def is_exclusive(self) -> bool:
       """Whether the tool is exclusive or not."""
       return self.settings.is_exclusive
   ```

#### 4. **Enable/Disable Status**
   - **`is_enabled`**: Specifies whether the tool is available for use.

   ```python
   def is_enabled(self) -> bool:
       """Whether the tool is enabled or not."""
       return self.settings.is_enabled
   ```

#### 5. **Control Takeover**
   - **`takes_control`**: Indicates if the tool takes over the conversation from the orchestrator. This is useful for tools like deep research, which require uninterrupted interaction with the user.

   ```python
   def takes_control(self):
       """
       Indicates whether the tool takes control of the conversation.
       """
       return False
   ```

---

### 📜 Tool Description and Prompts

The `Tool` class provides several methods for describing the tool and generating prompts for both the system and the user. These descriptions and prompts help the orchestrator and LLMs understand the tool's purpose and how to interact with it.

#### Tool Description
```python
@abstractmethod
def tool_description(self) -> LanguageModelToolDescription:
    """
    Provides a detailed description of the tool.

    Returns:
        LanguageModelToolDescription: The tool's description.
    """
    raise NotImplementedError
```

#### System Prompts
```python
def tool_description_for_system_prompt(self) -> str:
    """Provides a detailed description for system-level understanding."""
    return ""

def tool_format_information_for_system_prompt(self) -> str:
    """Provides formatting instructions for system-level responses."""
    return ""
```

#### User Prompts
```python
def tool_description_for_user_prompt(self) -> str:
    """Provides a description for user-facing interactions."""
    return ""

def tool_format_information_for_user_prompt(self) -> str:
    """Provides formatting instructions for user-facing responses."""
    return ""

def tool_format_reminder_for_user_prompt(self) -> str:
    """
    Provides a short reminder for formatting rules for the user prompt.
    """
    return ""
```

#### 📦 Tool Prompts

The `get_tool_prompts` method consolidates all tool-related information into a `ToolPrompts` object, making it easier for the orchestrator to inject this data into jinja templates on rendering the system and the user prompt.

#### Method:
```python
def get_tool_prompts(self) -> ToolPrompts:
    """
    Collects all tool-related information for templating.

    Returns:
        ToolPrompts: The consolidated tool information.
    """
    return ToolPrompts(
        name=self.name,
        display_name=self.display_name(),
        tool_description=self.tool_description().description,
        tool_system_prompt=self.tool_description_for_system_prompt(),
        tool_format_information_for_system_prompt=self.tool_format_information_for_system_prompt(),
        input_model=self.tool_description_as_json(),
        tool_user_prompt=self.tool_description_for_user_prompt(),
        tool_format_information_for_user_prompt=self.tool_format_information_for_user_prompt(),
    )
```






