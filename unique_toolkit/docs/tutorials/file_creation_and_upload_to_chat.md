# Document Upload to Chat Interface

This tutorial shows how to upload documents to a chat interface and create references that users can interact with.

## What You'll Learn

- Creating assistant messages in a chat
- Uploading content from bytes to the content service
- Creating proper content references
- Modifying messages to include document references

## Implementation

### Step 1: Create Initial Message

Start with a placeholder message to inform the user that the document creation process has begun:

```{.python #upload_with_reference_initial_message}

assistant_message =chat_service.create_assistant_message(
    content="Hi there, the agent has started to create your document.",
)
```

### Step 2: Prepare Document Content

Convert your document to bytes. In this example, we're using simple text, but this could be any file format:

```{.python #upload_with_reference_document_creation}
content_bytes = b"Hello, world!"
```

### Step 3: Upload Content to Service

Use the content service to upload the bytes with proper metadata. The `skip_ingestion=True` parameter prevents automatic content processing, which is useful for simple file sharing:

```{.python #upload_with_reference_upload_document}
uploaded_content = content_service.upload_content_from_bytes(
        content=content_bytes,
        content_name="document.txt",
        mime_type="text/plain",
        chat_id=event.payload.chat_id,
        skip_ingestion=True,
    )
```

### Step 4: Create Reference and Update Message

Build a `ContentReference` object that links the uploaded content to the message, then modify the original message to include the reference:

```{.python #upload_with_reference_referencing_in_message}
reference = ContentReference(
        id=uploaded_content.id,
        sequence_number=1,
        message_id=event.payload.assistant_message.id,
        name="document.txt",
        source=event.payload.name,
        source_id=event.payload.chat_id,
        url=f"unique://content/{uploaded_content.id}",
    )


chat_service.modify_assistant_message(
                content="Please find the translated document below in the references.",
                message_id=assistant_message.id, 
                references=[reference],
            )
```

### Step 5: Allow New User Input

Finally, lets not forget to free the user text area again such that a new message can be typped.
```{.python #free_user_input}
chat_service.free_user_input()
```



<!--
```{.python file=docs/.python_files/upload_to_chat.py}
<<full_sse_setup>>
    settings.update_from_event(event)
    <<init_services_from_event>>
    <<upload_with_reference_initial_message>>
    <<upload_with_reference_document_creation>>
    <<upload_with_reference_upload_document>>
    <<upload_with_reference_referencing_in_message>>
    <<free_user_input>>
```
-->


??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [File Upload to Chat with Reference](../examples_from_docs/upload_to_chat.py)
    <!--/codeinclude-->



