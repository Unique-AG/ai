## 🧠 Planning vs. Executing

### _plan_or_execute() Generate answer or request the tool calls:

Decides how to call the model:
- Builds messages via `_compose_message_plan_execution()` (which renders prompts and history). These are the instructions for the LLMs the context on which it will build it's next action. To either call tools to gather more information or to stream a message.
- Case 1: If forced tools exist and it’s the first iteration → call LLM once per `toolChoice`, merge tool calls and references across responses.
- Case 2: If it’s the last iteration → do not provide tools; force the model to answer.
- Case 3: Default → provide tools; let the model decide to call tools or stream content.

The method always returns a `LanguageModelStreamResponse` which can includes:
- `message.text` or/and
- `tool_calls`
 
This makes heavy use of the function `complete_with_references_async`, it is described in detail here LINK. 
In a nutshell it either streams a response from the llm or/and it returns the decision from the LLM that more tools need to be used, in oder for the LLM to answer
Should it stream it makes sure the references are automatically cited correctly and with proper linkage so it can be displayed to the user.

**Flow diagram:**
Detailed description of Step A from the Main Control flow:

![Answer or request tool calls](answer_or_request_tool_calls.png)

Code:
```python
    # @track()
    async def _plan_or_execute(self) -> LanguageModelStreamResponse:
        self._logger.info("Planning or executing the loop.")
        messages = await self._compose_message_plan_execution()

        self._logger.info("Done composing message plan execution.")

        # Forces tool calls only in first iteration
        if (
              len(self._tool_manager.get_forced_tools()) > 0
            and self.current_iteration_index == 0
        ):
            self._logger.info("Its needs forced tool calls.")
            self._logger.info(
                  f"Forced tools: {self._tool_manager.get_forced_tools()}"
            )
            responses = [
                  await self._chat_service.complete_with_references_async(
                      messages=messages,
                    model_name=self._config.space.language_model.name,
                    tools=self._tool_manager.get_tool_definitions(),
                    content_chunks=self._reference_manager.get_chunks(),
                    start_text=self.start_text,
                    debug_info=self._debug_info_manager.get(),
                    temperature=self._config.agent.experimental.temperature,
                    other_options=self._config.agent.experimental.additional_llm_options
                    | {"toolChoice": opt},
                )
                for opt in self._tool_manager.get_forced_tools()
            ]

            # Merge responses and refs:
            tool_calls = []
            references = []
            for r in responses:
                if r.tool_calls:
                    tool_calls.extend(r.tool_calls)
                references.extend(r.message.references)

            stream_response = responses[0]
            stream_response.tool_calls = (
                  tool_calls if len(tool_calls) > 0 else None
            )
            stream_response.message.references = references
        elif (
              self.current_iteration_index
            == self._config.agent.max_loop_iterations - 1
        ):
            self._logger.info(
                  "we are in the last iteration we need to produce an answer now"
            )
            # No tool calls in last iteration
            stream_response = await self._chat_service.complete_with_references_async(
                  messages=messages,
                model_name=self._config.space.language_model.name,
                content_chunks=self._reference_manager.get_chunks(),
                start_text=self.start_text,
                debug_info=self._debug_info_manager.get(),
                temperature=self._config.agent.experimental.temperature,
                other_options=self._config.agent.experimental.additional_llm_options,
            )

        else:
            self._logger.info(
                  f"we are in the iteration {self.current_iteration_index} asking the model to tell if we should use tools or if it will just stream"
            )
            stream_response = await self._chat_service.complete_with_references_async(
                  messages=messages,
                model_name=self._config.space.language_model.name,
                tools=self._tool_manager.get_tool_definitions(),
                content_chunks=self._reference_manager.get_chunks(),
                start_text=self.start_text,
                debug_info=self._debug_info_manager.get(),
                temperature=self._config.agent.experimental.temperature,
                other_options=self._config.agent.experimental.additional_llm_options,
            )

        return stream_response
```