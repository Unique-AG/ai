# Chat and Message Memories

The `ChatService` is a has the ability to add additional memories to the messages

## Basics

### Create assistant messages

The most used functionality is to create an assistant message via a stream to the frontend


```{.python #chat_service_chat_memory}

try:
    old_memory = chat_service.find_chat_memory(key="user_message")
    print(old_memory)
except Exception as e:
    print(f"No chat memory found with key 'user_message'")


chat_service.create_chat_memory(
        key="user_message",
        value={"test_memory": "test_value"})

chat_service.complete_with_references(
        messages = messages,
        model_name = LanguageModelName.AZURE_GPT_4o_2024_1120)
```


<!--

```{.python file=docs/.python_files/chat_service_chat_memory.py}
<<full_sse_setup_with_services>>
    <<trivial_message_from_user>>
    <<chat_service_chat_memory>>
```
-->
