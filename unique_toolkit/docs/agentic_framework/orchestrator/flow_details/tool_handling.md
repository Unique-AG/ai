# 🔧 Tool Handling

## _handle_tool_calls()

When the LLM returns tool calls:
1. Append tool calls to history
2. Execute tool calls via ToolManager
3. Extract referenceable chunks from tool results
4. Collect debug info from tools
5. Add tool results to history
6. Return whether a tool took control (to exit the loop if true)

When the model proposes tool calls, the orchestrator has to do more than merely “run them.”

Here’s the reasoning behind each step:

1. Append tool calls to history — before execution
The conversation history must reflect the model’s intent at the moment it decided to act. By writing the tool calls into the HistoryManager first, we preserve a verifiable chain of decision → action. This makes subsequent model calls reproducible: on the next iteration, the LLM sees exactly which tools it requested and in what order.
2. Execute tool calls via ToolManager
The ToolManager centralizes the parallel execution of the tools. Keeping execution behind a single interface reduces coupling in the orchestrator and ensures every tool adheres to a consistent contract.

3. Extract referenceable chunks from tool results
Tools can produce citable references as part of the `ToolCallResponse`. The ReferenceManager collects them to allow the citation by the model during the execution of `complete_with_references_async`. 
Multiple tools can produce citable references and all of them must be numbered correctly and brought into a standardized format for citation by the ReferenceManager.

4. Collect debug info from tools
Operational visibility matters. If a tool times out, returns a partial payload, or hits an API limit, the DebugInfoManager captures this without polluting the user-facing content. These traces are invaluable for developer diagnosis and for adaptive logic (e.g., future retries, fallbacks).
For easier debugging in production and richer telemetry without exposing noisy internals to end users.
5. Add tool results to history
Mich like in "Append tool calls to history" step the The model’s next reasoning step must be informed about the actual tool outputs (not just that a tool was called). 
6. Return whether a tool “takes control”
Some tools aren’t just data fetchers — they’re specialized agents (e.g., deep research, long-running pipelines) that assume full streaming and control. If ToolManager.does_a_tool_take_control() returns true, the orchestrator stops its loop to handoff control to the subagent.

This ordering preserves causal integrity (what was intended vs. what happened), equips the next iteration with usable evidence, and makes space for expert agents to take over when it’s appropriate.




Code:
```python
    async def _handle_tool_calls(
          self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        """Handle the case where tool calls are returned."""
        self._logger.info("Processing tool calls")

        tool_calls = loop_response.tool_calls or []

        # Append function call to history
        self._history_manager._append_tool_calls_to_history(tool_calls)

        # Execute tool calls
        tool_call_responses = await self._tool_manager.execute_selected_tools(
              tool_calls
        )

        # Process results with error handling
        self._reference_manager.extract_referenceable_chunks(
              tool_call_responses
        )
        self._debug_info_manager.extract_tool_debug_info(tool_call_responses)
        self._history_manager.add_tool_call_results(tool_call_responses)

        return self._tool_manager.does_a_tool_take_control(tool_calls)
```

Notes:
- “Tool takes control” scenarios (e.g., deep research) stop the orchestrator’s loop and hand over streaming to the tool/agent.
