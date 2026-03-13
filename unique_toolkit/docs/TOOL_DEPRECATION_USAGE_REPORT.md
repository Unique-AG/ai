# Tool Deprecation Usage Report

## Summary

The `Tool` base class in `agentic/tools/tool.py` currently depends on deprecated components:

- **ChatEvent** – passed to `__init__`, used to create ChatService and LanguageModelService
- **ChatService** – created from event, exposed via deprecated `chat_service` property
- **LanguageModelService** – created from event, exposed via deprecated `language_model_service` property
- **ToolProgressReporter** – passed to `__init__`, exposed via deprecated `tool_progress_reporter` property
- **MessageStepLogger** – created from ChatService (chat-frontend tied)

## Usage Map

| Component | Tool Base | DeepResearchTool | PMPositionsTool | MCPToolWrapper | SubAgentTool |
|-----------|-----------|------------------|-----------------|----------------|--------------|
| event | init/store | ~30 usages | 0 | ~8 usages | init (user_id, company_id, chat_id) |
| chat_service | creates | ~25 usages | 0 | 0 | 0 |
| language_model_service | creates | 1 (pass to agent) | 1 (complete_async) | 0 | 0 |
| tool_progress_reporter | init/store | pass-through | 0 | 3 usages | 1 usage |
| _message_step_logger | creates | 0 | 0 | 1 | 1 |

## Other Call Sites

- **ToolManager** – passes `event` and `tool_progress_reporter` to `ToolFactory.build_tool_with_settings()`
- **A2AManager** – passes `tool_progress_reporter` when building sub-agents
- **MCPManager** – passes `tool_progress_reporter` when creating MCP tools

## Migration Direction (per target_architecture.md)

The Agentic Framework should depend on **protocols**, not concrete platform services. Tools should receive "injectable dependencies" at invocation time.

**Proposed**: Introduce `ToolRunContext` passed to `run()`, containing the services a tool needs. ToolManager builds the context from the event and injects it when executing tools.
