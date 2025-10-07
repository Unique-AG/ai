# Chat Service - Image and Document Handling

This tutorial demonstrates how to handle images and documents uploaded to a chat session. The Chat Service provides convenient methods to retrieve and process various types of content that users upload during conversations.

## Overview

When users upload images or documents through the chat interface, you can:
- Download and retrieve uploaded content
- Process images to include them in model prompts
- Handle documents for analysis or context
- Build messages that combine text and visual content

<!--

```{.python file=docs/.python_files/minimal_chat_document_app.py}
<<full_sse_setup_with_services>>
    <<chat_service_document_and_image_download>>
    <<chat_service_images_message_building>>
    <<chat_service_send_message>>
```
-->

## Downloading Images and Documents

The `download_chat_images_and_documents()` method retrieves all images and documents that have been uploaded to the current chat session. This returns two separate lists: one for images and one for other document types.

```{.python #chat_service_document_and_image_download}
images, documents = chat_service.download_chat_images_and_documents()

if len(documents) > 0:
    doc_bytes = chat_service.download_chat_content_to_bytes(content_id=documents[0].id)

```

Once you have the list of uploaded content, you can download the actual bytes of any specific file using `download_chat_content_to_bytes()`. This is useful for processing documents or passing images to vision-capable language models.

## Building Messages with Images

To send images to vision-capable models, you need to construct multi-part messages that include both text and image content. The `OpenAIUserMessageBuilder` makes this easy by providing methods to append different content types.

```{.python #chat_service_images_message_building}
img_bytes = None
img_mime_type = None
if len(images) > 0:
    img_bytes = chat_service.download_chat_content_to_bytes(content_id=images[0].id)
    img_mime_type, _ = mimetypes.guess_type(images[0].key)

builder = (OpenAIMessageBuilder()
        .system_message_append(content="You are a helpful assistant."))

if img_bytes is not None and img_mime_type is not None:
    builder.user_message_append(
            content=OpenAIUserMessageBuilder()
            .append_text("What is the content of the image?")
            .append_image(content=img_bytes, mime_type=img_mime_type)
            .iterable_content
        )
else:
    builder.user_message_append(content="Can you see the image? If not, say so.")


```

In this example:
1. We download the image bytes and determine the MIME type (e.g., `image/png`, `image/jpeg`)
2. We create an `OpenAIMessageBuilder` to construct the message sequence
3. We use `OpenAIUserMessageBuilder` to create a multi-part user message containing both text and the image
4. The `.iterable_content` property provides the properly formatted content for the API

## Sending the Message

Once your message is built with all the necessary content, you can send it to the language model and stream the response back to the user.

```{.python #chat_service_send_message}
chat_service.complete_with_references(
    messages=builder.messages,
    model_name=LanguageModelName.AZURE_GPT_4o_2024_1120
)

chat_service.free_user_input()
```

The `complete_with_references()` method:
- Sends the messages to the specified language model (in this case, GPT-4o with vision capabilities)
- Automatically streams the response back to the chat interface
- Handles reference management if the model returns any citations

Finally, `free_user_input()` re-enables the chat input field, allowing the user to send another message. This should be called after the model completes its response to restore interactivity.

## Key Considerations

- **Vision Models**: Use vision-capable models like GPT-4o when processing images
- **MIME Types**: Ensure you provide the correct MIME type for images
- **Error Handling**: Always check if images/documents exist before processing
- **Memory Usage**: Large images and documents consume memory; consider processing strategies for multiple files
