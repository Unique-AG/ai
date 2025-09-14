## 🧩 Plan Processing

### _process_plan()


- If tool calls are present → handle tools via `_handle_tool_calls()` and return whether a tool took control (if so, exit loop).
  - A tool can take control if its an agent itself and takes over the communication with the user e.g. the DeepResearch tool.
- If no tool calls → handle finalization via `_handle_no_tool_calls()` and exit the loop.

- If the model response is empty → warn the user and exit the loop. This case normally never happens in LLMs, it is more of a precaution.


**Flow diagram:**
Detailed description of Step D from the Main Control flow


![Agent Control Flow](execute_tool.png)

Code:
```python
    async def _process_plan(
          self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        self._logger.info(
              "Processing the plan, executing the tools and checking for loop exit conditions once all is done."
        )

        if loop_response.is_empty():
            self._logger.debug("Empty model response, exiting loop.")
            self._chat_service.modify_assistant_message(
                  content=EMPTY_MESSAGE_WARNING
            )
            return True

        call_tools = len(loop_response.tool_calls or []) > 0
        if call_tools:
            self._logger.debug(
                  "Tools were called we process them and do not exit the loop"
            )

            return await self._handle_tool_calls(loop_response)

        self._logger.debug("No tool calls. we might exit the loop")

        return await self._handle_no_tool_calls(loop_response)
```