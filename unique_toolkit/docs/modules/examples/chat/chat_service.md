
# Chat Service - Basics

<!--
```{.python #import_language_model_name}
from unique_toolkit import LanguageModelName
```
-->

<!--
```{.python #trivial_message_from_user}
messages = (
        OpenAIMessageBuilder()
        .system_message_append(content="You are a helpful assistant")
        .user_message_append(content=event.payload.user_message.text)
        .messages
    )
```
-->



The chat service is responsible for all interactions with the Unique chat frontend as seen below

![alt text](./images/chat_frontend.png)


The following elements are directly influenced by it.

| Element | Description | 
|--|--------|
| User Message | The request as entered by the user |
| Assistant Message | The answer of the agent/workflow or LLM |
| Json Value | The final request sent to the LLM that creates the assistant message|
| Debug Info | Debug information generated during the processing of the request|


The `ChatService` from the `unique_toolkit` is used to communicate to these elments. Please see [Event Driven Applications](../../../application_types/event_driven_applications.md) on how to initialize services and setup a development setup. The service itself can be imported as

```{python #unique_chat_service_import}
from unique_toolkit import ChatService
```

## Chat State

The `ChatService` is a stateful service and therefore should be freshly instantiated for each request sent by a user from the frontend. 

## Create assistant messages

The most used functionality is to create an assistant message via a stream to the frontend


```{.python #chat_service_complete_with_references}
chat_service.complete_with_references(
        messages = messages,
        model_name = LanguageModelName.AZURE_GPT_4o_2024_1120)
```


<!--

```{.python file=docs/.python_files/chat_app_minimal.py}
<<full_sse_setup_with_services>>
    <<trivial_message_from_user>>
    <<chat_service_complete_with_references>>
```
-->


Alternatively a message can be created directly by

```{python #chat_service_create_assistant_message}
assistant_message = chat_service.create_assistant_message(
        content="Hello from Unique",
    )
```

<!--
```{.python file=docs/.python_files/chat_with_manual_message_create.py}
<<full_sse_setup_with_services>>
    <<chat_service_create_assistant_message>>
```
-->

??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [Simple Streaming](../../../examples_from_docs/chat_app_minimal.py)
    [Simple Manual Response](../../../examples_from_docs/chat_with_manual_message_create.py)
    <!--/codeinclude-->

## Modifying messages

## Edit texts 

Both user messages as well as assistant message may be modified via the `message_id`. If no id is specified the last message in the chat history will be modified.

```{python #chat_service_modify_user_message}
chat_service.modify_user_message(
        content="Modified User Message",
        message_id=event.payload.user_message.id,
    )
```

```{python #chat_service_modify_assistant_message}
chat_service.modify_assistant_message(
        content="Modified User Message",
        message_id=assistant_message.id
    )
```

<!--
```{.python file=docs/.python_files/chat_with_manual_message_create_and_modification.py}
<<full_sse_setup_with_services>>
    <<chat_service_create_assistant_message>>
    <<chat_service_modify_assistant_message>>
```
-->

## Unblocking the next user input

For each user interaction the plattform is expected to answer in some form. 
Thus, the user input is blocked during the process leading to this answer as seen below. 

![alt text](./images/chat_window_active_stop_button.png)

It can be unblocked using 

```{python #chat_service_free_user_input}
chat_service.free_user_input()
```

<!--
```{.python file=docs/.python_files/chat_with_manual_message_create_free_user_input.py}
<<full_sse_setup_with_services>>
    <<chat_service_create_assistant_message>>
    <<chat_service_modify_assistant_message>>
    <<chat_service_free_user_input>>
```
-->

which should be called at the end of an agent interaction. Alternatively the user input can be freed by setting the `set_completed_at` flag in `create_assistant_message` or `modify_assistant_message`.


## Adding References

For applications using additional information retrieved from the knowledge base or external Apis references are an important measure to verify the generated text from the LLM. Additionally, references can also be used on deterministically created assitant message as in the following example 

```{python #chat_service_assistant_message_with_reference}
chat_service.create_assistant_message(
        content="Hello from Unique <sup>0</sup>",
        references=[ContentReference(source="source0",
                                     url="https://www.unique.ai",
                                     name="reference_name",
                                     sequence_number=0,
                                     source_id="source_id_0",
                                     id="id_0")]
    )
```

In the `content` string the refercnes must be referred to by `<sup>sequence_number</sub>`. The name property of the `ContentReference` will be displayed on the reference component and below the message as seen below

![alt text](.images/chat_with_reference.png)

<!--
```{.python file=docs/.python_files/chat_with_manual_message_and_reference.py}
<<full_sse_setup>>
    chat_service = ChatService(event)
    <<chat_service_create_assistant_message>>
    <<chat_service_modify_assistant_message>>
    <<chat_service_assistant_message_with_reference>>
```
-->


## Referencing Content Chunks when streaming to the frontend

Lets assume that the vector search has retrieved the following chunks

```{python #chat_service_retrieved_chunks}
chunks = [ContentChunk(text="Unique is a company that provides the platform for AI-powered solutions.",
                                     order=0,
                                     chunk_id="chunk_id_0",
                                     key="key_0",
                                     title="title_0",
                                     start_page=1,
                                     end_page=1,
                                     url="https://www.unique.ai",
                                     id="id_0"),
          ContentChunk(text="Unique is your Responsible AI Partner, with extensive experience in implementing AI solutions for enterprise clients in financial services.",
                                     order=1,
                                     chunk_id="chunk_id_1",
                                     key="key_1",
                                     title="title_1",
                                     start_page=1,
                                     end_page=1,
                                     url="https://www.unique.ai",
                                     id="id_1")
                                     ]
```

If we want the LLM be able to reference them in its answer we need to present the information nicely, e.g. in a markdown table

```{python #chat_service_chunk_presentation}
def to_source_table(chunks: list[ContentChunk]) -> str:
    header = "| Source Number | Title |  URL | \n" + "| --- | --- | --- | --- |\n"
    rows = [f"| {index} | {chunk.title} | {chunk.url} |\n" for index,chunk in enumerate(chunks)]
    return header + "\n".join(rows)
```

The index of the list here is important as the backend requires to match the output of the LLM to the content chunk, for this we use the following reference guidelines as part of the system prompt.


```{python #chat_service_reference_guidelines}
reference_guidelines = """
Whenever you use information retrieved with a tool, you must adhere to strict reference guidelines. 
You must strictly reference each fact used with the `source_number` of the corresponding passage, in 
the following format: '[source<order_number>]'.

Example:
- The stock price of Apple Inc. is $150 [source0] and the company's revenue increased by 10% [source1].
- Moreover, the company's market capitalization is $2 trillion [source2][source3].
- Our internal documents tell us to invest[source4] (Internal)
"""
```




The message to the LLM could now look like this

```{python #chat_service_streaming_call_with_sources}
messages = (
        OpenAIMessageBuilder()
        .system_message_append(content=f"You are a helpful assistant. {reference_guidelines}")
        .user_message_append(content=f"<Sources> {to_source_table(chunks)}</Srouces>\n\n User question: {event.payload.user_message.text}")
        .messages
    )

chat_service.complete_with_references(
        messages=messages, 
        model_name=LanguageModelName.AZURE_GPT_4o_2024_1120,
        content_chunks=chunks)
```

![alt text](./images/chat_references_with_streaming.png)

<!--
```{.python file=docs/.python_files/chat_with_streamed_references.py}
<<full_sse_setup>>
    chat_service = ChatService(event)
    <<chat_service_retrieved_chunks>>
    <<chat_service_chunk_presentation>>
    <<chat_service_reference_guidelines>>
    <<chat_service_streaming_call_with_sources>>
```
-->







## Debug Information
Debuging information can be added to both the user and assistant messages but only the debug information that is added to the user message will be shown in the chat frontend.

Therefore we recommend to use 

```{python #chat_service_modify_user_message_debug_info}

debug_info = event.get_initial_debug_info()
debug_info.update({"timing": "20s till completion"})


chat_service.modify_user_message(
        content="Modified User Message",
        message_id=event.payload.user_message.id,
        debug_info=debug_info
    )
```
<!--
```{.python file=docs/.python_files/chat_edit_debug_information.py}
<<full_sse_setup_with_services>>
    <<chat_service_create_assistant_message>>
    <<chat_service_modify_assistant_message>>
    <<chat_service_modify_user_message_debug_info>>
    <<chat_service_free_user_input>>
```
-->


The debug information will be updated after a refresh of the page and look as follows

![alt text](../../../debug_info_update.png)

??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [Modifying Assistant Message](../../../examples_from_docs/chat_with_manual_message_create_and_modification.py)
    [Unblocking](../../../examples_from_docs/chat_with_manual_message_create_free_user_input.py)
    [Debug Information](../../../examples_from_docs/chat_edit_debug_information.py)
    <!--/codeinclude-->




## Message Assessments

Once an assistant has answered its time to access the quality of its answer. This happense usually through an LLM call to a more sophisticated or a task specialized LLM. The result of the assessment can be reported  using the message assessments by the Unique plattform.

<!--
```{python #message_assessment_imports}
from unique_toolkit.chat.schemas import ChatMessageAssessmentStatus, ChatMessageAssessmentType, ChatMessageAssessmentLabel
```
-->
```{python #chat_service_create_message_assessment}
if not assistant_message.id:
    raise ValueError("Assistant message ID is not set")

message_assessment = chat_service.create_message_assessment(
        assistant_message_id=assistant_message.id,
        status=ChatMessageAssessmentStatus.PENDING,
        type=ChatMessageAssessmentType.COMPLIANCE,
        title="Following Guidelines",
        explanation="",
        is_visible=True,
    )
```

During the assessment a pending indication can be shown as below. 
![alt text](./../../../pending_message_assessment.png)

Once the assessment is finished it can be reported using

```{python #chat_service_modify_message_assessment}
chat_service.modify_message_assessment(
    assistant_message_id=assistant_message.id,
    status=ChatMessageAssessmentStatus.DONE,
    type=ChatMessageAssessmentType.COMPLIANCE,
    title="Following Guidelines",
    explanation="The agents choice of words is according to our guidelines.",
    label=ChatMessageAssessmentLabel.GREEN,
)
```

which displays as
![alt text](./../../../finished_message_assessment.png)

<!--
```{.python file=docs/.python_files/chat_with_message_assessment.py}
<<common_imports>>
<<full_sse_setup_with_services>>
    <<chat_service_create_assistant_message>>
    <<chat_service_create_message_assessment>>
    <<chat_service_modify_message_assessment>>
```
-->

