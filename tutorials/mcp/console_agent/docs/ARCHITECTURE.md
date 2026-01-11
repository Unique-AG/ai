# Console Agent Architecture

This document describes the architecture of the MCP Console Agent, an interactive AI assistant with Model Context Protocol (MCP) server integration.

## Overview

The Console Agent is a terminal-based AI assistant that connects to MCP servers to extend its capabilities with external tools. It follows SOLID principles and uses a modular architecture for maintainability and testability.

```mermaid
flowchart TB
    subgraph User["👤 User"]
        Terminal[Terminal Input/Output]
    end

    subgraph ConsoleAgent["Console Agent"]
        Orchestrator[AgentOrchestrator]
        Runner[InteractiveRunner]
        UI[ConsoleUI]
        Factory[AgentFactory]
        MCPSvc[MCPService]
        Tracker[TokenTracker]
    end

    subgraph External["External Services"]
        OpenAI[OpenAI API]
        MCP[MCP Server]
    end

    Terminal <--> UI
    UI <--> Runner
    Runner --> Orchestrator
    Orchestrator --> Factory
    Orchestrator --> MCPSvc
    Factory --> Agent[pydantic-ai Agent]
    Agent --> OpenAI
    Agent --> MCP
    Runner --> Tracker
```

## Module Structure

```mermaid
graph LR
    subgraph Package["console_agent"]
        agent["agent.py<br/><i>Entry Point & Orchestration</i>"]
        factory["agent_factory.py<br/><i>Agent Creation</i>"]
        mcp["mcp_service.py<br/><i>MCP Connection</i>"]
        ui["console_ui.py<br/><i>Rich Console UI</i>"]
        runner["interactive_runner.py<br/><i>REPL Loop</i>"]
        tracker["token_tracker.py<br/><i>Usage Tracking</i>"]
        protocols["protocols.py<br/><i>Interfaces</i>"]
    end

    agent --> factory
    agent --> mcp
    agent --> ui
    agent --> runner
    agent --> tracker
    runner --> ui
    runner --> tracker
    mcp --> protocols
    tracker --> protocols
```

## Component Details

### 1. Agent Orchestrator (`agent.py`)

The main entry point that coordinates all components. Handles:
- MCP server availability checking
- Agent creation with proper configuration
- Token tracker initialization
- Running the interactive loop

```mermaid
sequenceDiagram
    participant User
    participant CLI as cli_main()
    participant Orch as AgentOrchestrator
    participant MCP as MCPService
    participant Factory as AgentFactory
    participant Runner as InteractiveRunner

    User->>CLI: Start application
    CLI->>Orch: Create & run()
    Orch->>MCP: check_server_available()
    MCP-->>Orch: MCPConnectionResult
    Orch->>Factory: create(config)
    Factory-->>Orch: Agent
    Orch->>Runner: run()
    Runner->>User: Interactive loop
```

### 2. Agent Factory (`agent_factory.py`)

Factory pattern implementation for creating pydantic-ai agents. Supports:
- Configurable instructions via `InstructionProvider` protocol
- MCP toolset integration with OAuth
- Model selection

```mermaid
classDiagram
    class AgentFactory {
        -openai_client: AsyncOpenAI
        -instruction_provider: InstructionProvider
        +create(config: AgentConfig) Agent
        -_create_toolsets(config) list~FastMCPToolset~
    }

    class AgentConfig {
        +model: str
        +mcp_server_url: str?
        +use_oauth: bool
        +tools_available: bool
        +mcp_client: Any?
        +instruction_provider: InstructionProvider
    }

    class InstructionProvider {
        <<protocol>>
        +get_instructions(tools_available: bool) str
    }

    class DefaultInstructionProvider {
        -instructions: AgentInstructions
        +get_instructions(tools_available: bool) str
    }

    class AgentInstructions {
        +with_tools: str
        +without_tools: str
    }

    AgentFactory --> AgentConfig
    AgentFactory --> InstructionProvider
    DefaultInstructionProvider ..|> InstructionProvider
    DefaultInstructionProvider --> AgentInstructions
```

### 3. MCP Service (`mcp_service.py`)

Manages MCP server connections and client lifecycle:
- Server availability checking with timeout
- OAuth authentication handling
- Client creation and tool listing

```mermaid
classDiagram
    class MCPService {
        -default_timeout: float
        -use_oauth: bool
        +check_server_available(url, timeout) MCPConnectionResult
        +create_client(url, use_oauth) Client
        +list_tools(client) list
    }

    class MCPConnectionResult {
        +available: bool
        +client: Any?
        +error: str?
    }

    MCPService --> MCPConnectionResult
```

### 4. Interactive Runner (`interactive_runner.py`)

REPL (Read-Eval-Print Loop) implementation:
- User input parsing and command detection
- Conversation state management
- Agent execution with error handling

```mermaid
stateDiagram-v2
    [*] --> WaitingForInput
    WaitingForInput --> ProcessingCommand: User enters text
    ProcessingCommand --> WaitingForInput: Empty input
    ProcessingCommand --> HistoryCleared: "clear/reset/new"
    ProcessingCommand --> RunningAgent: Question
    ProcessingCommand --> [*]: "quit/exit/q"
    HistoryCleared --> WaitingForInput
    RunningAgent --> DisplayingResponse: Success
    RunningAgent --> DisplayingError: Error
    DisplayingResponse --> WaitingForInput
    DisplayingError --> WaitingForInput
```

```mermaid
classDiagram
    class InteractiveRunner {
        -agent: Agent
        -ui: ConsoleUI
        -debug: bool
        -state: ConversationState
        +run(initial_question?) void
        -_handle_iteration(question?) UserCommand
        -_process_question(question) void
        -_run_agent(question) Any?
    }

    class ConversationState {
        +message_history: list?
        +token_tracker: TokenTracker
        +reset() void
        +update_history(messages) void
    }

    class InputHandler {
        +QUIT_COMMANDS: frozenset
        +CLEAR_COMMANDS: frozenset
        +parse_input(input) tuple
    }

    class UserCommand {
        <<enumeration>>
        QUIT
        CLEAR_HISTORY
        QUESTION
        EMPTY
    }

    InteractiveRunner --> ConversationState
    InteractiveRunner --> InputHandler
    InputHandler --> UserCommand
```

### 5. Console UI (`console_ui.py`)

Rich-based terminal UI with:
- Styled panels for user/agent messages
- Token usage progress bars
- Debug information display
- Tool usage indicators

```mermaid
classDiagram
    class ConsoleUI {
        -console: Console
        -config: UIConfig
        +print_welcome_banner(debug)
        +print_user_message(message)
        +print_agent_response(response)
        +print_tool_usage(tool_names)
        +print_token_usage(in, out, max)
        +print_error(message)
        +create_status(message) Status
    }

    class UIConfig {
        +panel_width_ratio: float
        +max_panel_width: int
        +progress_bar_width: int
        +content_preview_length: int
    }

    ConsoleUI --> UIConfig
```

### 6. Token Tracker (`token_tracker.py`)

Tracks cumulative token usage:
- Input/output token counting
- Usage percentage calculation
- Limit warnings

```mermaid
classDiagram
    class TokenTracker {
        -stats: TokenStats
        -max_tokens: int?
        +input_tokens: int
        +output_tokens: int
        +total_tokens: int
        +usage_percentage: float
        +add_usage(in, out)
        +add_from_result(result)
        +reset()
        +is_near_limit(threshold) bool
    }

    class TokenStats {
        +input_tokens: int
        +output_tokens: int
        +total_tokens: int
        +add(in, out)
        +reset()
    }

    class ModelInfoExtractor {
        +get_max_tokens(model_info) int?
        +extract_from_model(model) Any?
    }

    TokenTracker --> TokenStats
```

### 7. Protocols (`protocols.py`)

Interface definitions enabling dependency injection and testability:

```mermaid
classDiagram
    class MCPClientProtocol {
        <<protocol>>
        +list_tools() list
        +__aenter__()
        +__aexit__()
    }

    class ConsoleOutputProtocol {
        <<protocol>>
        +print(*args, **kwargs)
        +width: int
    }

    class AgentProtocol {
        <<protocol>>
        +run(prompt, history?) AgentRunResult
    }

    class AgentRunResult {
        <<protocol>>
        +output: str
        +all_messages() list
        +new_messages() list
        +usage() TokenUsage
    }

    class TokenUsage {
        <<protocol>>
        +input_tokens: int
        +output_tokens: int
    }

    class ModelInfoProtocol {
        <<protocol>>
        +max_tokens: int?
        +max_context: int?
        +context_window: int?
    }
```

## Data Flow

```mermaid
flowchart LR
    subgraph Input
        Q[User Question]
    end

    subgraph Processing
        Parse[Parse Input]
        History[Message History]
        Agent[pydantic-ai Agent]
        Tools[MCP Tools]
    end

    subgraph Output
        Response[Agent Response]
        Tokens[Token Usage]
        UI[Console Display]
    end

    Q --> Parse
    Parse --> Agent
    History --> Agent
    Agent <--> Tools
    Agent --> Response
    Agent --> Tokens
    Response --> UI
    Tokens --> UI
```

```mermaid
sequenceDiagram
    participant Agent as AgentOrchestrator
    participant Settings as get_mcp_settings()
    participant Auth as get_oauth_setting_for_server()
    participant MCP as MCPService
    participant Client as FastMCP Client

    Agent->>Settings: Load MCP_SERVERS config
    Settings-->>Agent: Parsed server configurations
    Agent->>Auth: Check OAuth for server.com
    Auth->>Settings: Get server settings
    Settings-->>Auth: Server-specific or default config
    Auth-->>Agent: OAuth setting for server.com
    Agent->>MCP: check_server_available("https://server.com")
    MCP->>Auth: Determine OAuth and timeout for server.com
    MCP->>Client: Client("https://server.com", auth="oauth")
    Client-->>MCP: Connected successfully
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| AI Framework | `pydantic-ai` | Agent orchestration and tool calling |
| MCP Client | `fastmcp` | Model Context Protocol integration |
| Console UI | `rich` | Terminal styling and formatting |
| Data Models | `pydantic` | Configuration and data validation |
| Async | `asyncio` | Asynchronous I/O operations |
| LLM Client | `openai` (AsyncOpenAI) | OpenAI API communication |

## SOLID Principles Applied

```mermaid
mindmap
  root((SOLID))
    SRP
      agent.py: Orchestration only
      console_ui.py: UI only
      mcp_service.py: MCP only
      token_tracker.py: Tracking only
    OCP
      InstructionProvider protocol
      Extensible without modification
    LSP
      All protocols substitutable
      Mock implementations for testing
    ISP
      Small focused protocols
      MCPClientProtocol
      ConsoleOutputProtocol
    DIP
      Depend on protocols
      Not concrete implementations
```

## Configuration

The agent accepts configuration through:

1. **Environment Variables**:
   - `MCP_SEARCH_DEBUG`: Enable debug mode (`true`/`1`/`yes`)
   - `MCP_SERVERS`: JSON dictionary of server configurations (see below)

2. **AgentConfig Dataclass**:
   - `model`: LLM model name
   - `mcp_server_url`: MCP server endpoint
   - `tools_available`: Enable/disable MCP tools
   - `mcp_client`: Optional pre-authenticated MCP client

3. **MCPServerSettings Model** (Pydantic BaseModel):
   - `oauth`: Whether to use OAuth authentication for this server
   - `timeout`: Connection timeout in seconds
   - `enabled`: Whether this server configuration is enabled

4. **MCPSettings Model** (Pydantic BaseSettings):
   - `servers`: Dictionary mapping server URLs to their settings
   - `default_oauth`: Default OAuth setting for unconfigured servers
   - `default_timeout`: Default timeout for unconfigured servers

**Note**: `MCPSettings` uses `pydantic_settings.BaseSettings` which automatically parses JSON from environment variables for complex types like `Dict[str, MCPServerSettings]`. This eliminates the need for manual JSON parsing.

5. **UIConfig Dataclass**:
   - `panel_width_ratio`: Response panel width
   - `max_panel_width`: Maximum panel width
   - `progress_bar_width`: Token bar width

### MCP Server Configuration

MCP servers are configured through a single `MCP_SERVERS` environment variable containing a JSON dictionary:

```bash
export MCP_SERVERS='{
  "https://secure-server.com": {
    "oauth": true,
    "timeout": 10.0,
    "enabled": true
  },
  "http://localhost:8080": {
    "oauth": false,
    "timeout": 5.0
  },
  "https://api.example.com/mcp": {
    "oauth": false,
    "enabled": false
  }
}'
```

**Configuration Options:**
- `oauth` (bool): Whether to use OAuth authentication (default: `true`)
- `timeout` (float): Connection timeout in seconds (default: `5.0`)
- `enabled` (bool): Whether this server is enabled (default: `true`)

**Additional Environment Variables:**
With `BaseSettings`, you can also override defaults directly:
- `MCP_DEFAULT_OAUTH`: Override default OAuth setting (default: `true`)
- `MCP_DEFAULT_TIMEOUT`: Override default timeout (default: `5.0`)

**Fallback Behavior:**
- Servers not in `MCP_SERVERS` use default settings:
  - `oauth`: `MCP_DEFAULT_OAUTH` or `true`
  - `timeout`: `MCP_DEFAULT_TIMEOUT` or `5.0` seconds
  - `enabled`: `true`

**Example Usage:**
```bash
# Production setup
MCP_SERVERS='{"https://mcp.prod.company.com": {"oauth": true, "timeout": 15}}' console-agent

# Development setup
MCP_SERVERS='{"http://localhost:8080": {"oauth": false, "timeout": 2}}' console-agent

# Mixed environment
MCP_SERVERS='{
  "https://mcp.prod.company.com": {"oauth": true},
  "http://localhost:8080": {"oauth": false}
}' console-agent
```

This approach provides clean, centralized configuration for all MCP server settings while maintaining backward compatibility through sensible defaults.

## Entry Points

```python
# Programmatic usage
from console_agent import main, AgentOrchestrator
await main(openai_client=client, debug=True)

# CLI usage (defined in pyproject.toml)
console-agent
```

## Error Handling

```mermaid
flowchart TD
    A[Agent Run] --> B{Success?}
    B -->|Yes| C[Display Response]
    B -->|No| D{Debug Mode?}
    D -->|Yes| E[Show Full Traceback]
    D -->|Yes| F[Show Captured Messages]
    D -->|No| G[Show Error Message]
    E --> H[Continue Loop]
    F --> H
    G --> H
```

The agent gracefully handles:
- MCP server unavailability (runs without tools)
- Network timeouts
- Authentication failures
- Agent execution errors

Debug mode provides detailed error information including captured messages before failure.

