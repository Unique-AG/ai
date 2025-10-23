# Chat Service - Advanced Rendering 


```{.python #rendering_prompt_buttons}
prompt_button_string = create_prompt_button_string(button_text="Click me", next_user_message="Next user message")
chat_service.create_assistant_message(
    content=f"Here is a prompt button:\n {prompt_button_string}",
)

```


<!--

```{.python file=docs/.python_files/chat_prompt_button.py}
<<full_sse_setup_with_services>>
    <<rendering_prompt_buttons>>
```
-->
