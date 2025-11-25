# Chat in Space Utility

Helper functions for interacting with spaces (assistants) asynchronously, including waiting for completions and chatting against files.

## Overview

The Chat in Space utilities provide:

- Async message sending with automatic polling
- Waiting for message completion
- File upload and chat workflows
- Ingestion completion tracking

## Methods

??? example "`unique_sdk.utils.chat_in_space.send_message_and_wait_for_completion` - Send message and wait"

    Sends a message to a space asynchronously and polls until completion.

    **Parameters:**

    - `user_id` (required) - User ID
    - `company_id` (required) - Company ID
    - `assistant_id` (required) - Assistant/Space ID
    - `text` (required) - Message text
    - `tool_choices` (optional) - List of tools to use (e.g., `["WebSearch", "InternalSearch"]`)
    - `scope_rules` (optional) - UniqueQL filter for document scope
    - `chat_id` (optional) - Existing chat ID (creates new chat if omitted)
    - `poll_interval` (optional) - Seconds between polls (default: 1.0)
    - `max_wait` (optional) - Maximum seconds to wait (default: 60.0)
    - `stop_condition` (optional) - When to stop: `"stoppedStreamingAt"` or `"completedAt"` (default: `"stoppedStreamingAt"`)

    **Returns:**

    - `Space.Message` object with the completed response

    **Example - Basic Usage:**

    ```python
    from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

    async def ask_assistant(question):
        message = await send_message_and_wait_for_completion(
            user_id=user_id,
            company_id=company_id,
            assistant_id="assistant_abc123",
            text=question
        )
        return message.text

    # Usage
    import asyncio
    answer = asyncio.run(ask_assistant("What is machine learning?"))
    print(answer)
    ```

    **Example - With Tools:**

    ```python
    message = await send_message_and_wait_for_completion(
        user_id=user_id,
        company_id=company_id,
        assistant_id="assistant_abc123",
        text="Research the latest AI developments",
        tool_choices=["WebSearch", "InternalSearch"],
        poll_interval=2.0,  # Check every 2 seconds
        max_wait=120.0  # Wait up to 2 minutes
    )
    ```

    **Example - With Scope Rules:**

    ```python
    message = await send_message_and_wait_for_completion(
        user_id=user_id,
        company_id=company_id,
        assistant_id="assistant_abc123",
        text="Search our engineering docs",
        tool_choices=["InternalSearch"],
        scope_rules={
            "or": [
                {
                    "operator": "contains",
                    "path": ["folderIdPath"],
                    "value": "uniquepathid://scope_engineering_docs"
                }
            ]
        }
    )
    ```

??? example "`unique_sdk.utils.chat_in_space.chat_against_file` - Upload file and chat"

    Uploads a file to a chat and sends a message, waiting for the response.

    **Parameters:**

    - `user_id` (required) - User ID
    - `company_id` (required) - Company ID
    - `assistant_id` (required) - Assistant/Space ID
    - `path_to_file` (required) - Local file path to upload
    - `displayed_filename` (required) - Filename to display
    - `mime_type` (required) - MIME type (e.g., `"application/pdf"`)
    - `text` (required) - Message to send after upload
    - `poll_interval` (optional) - Seconds between polls (default: 1.0)
    - `max_wait` (optional) - Maximum seconds to wait (default: 60.0)
    - `should_delete_chat` (optional) - Delete chat after completion (default: True)

    **Returns:**

    - `Space.Message` object with the response

    **Example:**

    ```python
    from unique_sdk.utils.chat_in_space import chat_against_file

    async def analyze_document(file_path):
        response = await chat_against_file(
            user_id=user_id,
            company_id=company_id,
            assistant_id="assistant_abc123",
            path_to_file=file_path,
            displayed_filename="report.pdf",
            mime_type="application/pdf",
            text="Summarize the key findings",
            should_delete_chat=True  # Clean up after
        )
        return response.text

    # Usage
    import asyncio
    summary = asyncio.run(analyze_document("/path/to/report.pdf"))
    ```

## Best Practices

??? example "Choose Appropriate Polling Settings"

    ```python
    # For quick responses
    await send_message_and_wait_for_completion(
        ...,
        poll_interval=0.5,  # Check every 0.5 seconds
        max_wait=30.0  # 30 second timeout
    )

    # For long-running operations
    await send_message_and_wait_for_completion(
        ...,
        poll_interval=2.0,  # Check every 2 seconds
        max_wait=300.0  # 5 minute timeout
    )
    ```

??? example "Use Stop Conditions Appropriately"

    ```python
    # Wait for streaming to stop (faster, may miss final processing)
    message = await send_message_and_wait_for_completion(
        ...,
        stop_condition="stoppedStreamingAt"  # Default
    )

    # Wait for full completion (slower, ensures complete response)
    message = await send_message_and_wait_for_completion(
        ...,
        stop_condition="completedAt"
    )
    ```

## Related Resources

- [Space API](../api_resources/space.md) - Direct space API methods
- [Message API](../api_resources/message.md) - Manage messages
- [File I/O](file_io.md) - Upload files before chatting
- [Content API](../api_resources/content.md) - Manage uploaded content

