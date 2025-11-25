# ChatCompletion API

The ChatCompletion API provides access to AI language models supported by Unique AI for generating text completions. (The request does not modify the frontend and is not related to any chats in the unique platform)

## Overview

Generate AI responses using various language models with OpenAI-compatible message format.

## Methods

??? example "`unique_sdk.ChatCompletion.create` - Generate AI completions"

    Send messages to an AI model and receive completions.

    **Parameters:**

    - `user_id` (required)
    - `company_id` (required)
    - `model` (required) - Model identifier (e.g., `"AZURE_GPT_4o_2024_1120"`)
    - `messages` (required) - Array of message objects in OpenAI format
    - `options` (optional) - Model parameters like temperature

    **Available Models:**

    Common models include:

    - `AZURE_GPT_4o_2024_1120` - GPT-4 Turbo
    - `AZURE_GPT_4_32K_0613` - GPT-4 with 32K context
    - `AZURE_o3_2025_0416` - Latest o3 model

    !!! tip
        Use [LLM Models API](llm_models.md) to get the current list of available models.

    **Example - Basic Completion:**

    ```python
    completion = unique_sdk.ChatCompletion.create(
        user_id=user_id,
        company_id=company_id,
        model="AZURE_GPT_4o_2024_1120",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain quantum computing in simple terms."}
        ]
    )

    print(completion.choices[0].message.content)
    ```

    **Example - With Options:**

    ```python
    completion = unique_sdk.ChatCompletion.create(
        user_id=user_id,
        company_id=company_id,
        model="AZURE_GPT_4o_2024_1120",
        messages=[
            {"role": "system", "content": "You are a creative storyteller."},
            {"role": "user", "content": "Write a short story about a robot."}
        ],
        options={
            "temperature": 0.8,      # Higher for more creativity
            "max_tokens": 500,
            "top_p": 0.9
        }
    )

    print(completion.choices[0].message.content)
    ```

    **Example - Multi-turn Conversation:**

    ```python
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "How do I reverse a string in Python?"},
        {"role": "assistant", "content": "You can use slicing: `reversed_str = my_str[::-1]`"},
        {"role": "user", "content": "Can you show me another way?"}
    ]

    completion = unique_sdk.ChatCompletion.create(
        user_id=user_id,
        company_id=company_id,
        model="AZURE_GPT_4o_2024_1120",
        messages=messages
    )

    print(completion.choices[0].message.content)
    ```

## Message Format

Messages follow the [OpenAI Chat API format](https://platform.openai.com/docs/api-reference/chat):

```python
{
    "role": "system" | "user" | "assistant",
    "content": "message text"
}
```

**Roles:**

- `system` - Instructions for the AI's behavior
- `user` - User messages
- `assistant` - AI responses (for conversation history)

## Use Cases

??? example "Structured Output Generation"

    ```python
    completion = unique_sdk.ChatCompletion.create(
        user_id=user_id,
        company_id=company_id,
        model="AZURE_GPT_4o_2024_1120",
        messages=[
            {
                "role": "system",
                "content": "Extract information as JSON: {\"name\": \"\", \"email\": \"\", \"phone\": \"\"}"
            },
            {
                "role": "user",
                "content": "John Doe, john@example.com, 555-0123"
            }
        ],
        options={"temperature": 0}
    )

    import json
    extracted_data = json.loads(completion.choices[0].message.content)
    ```

## Response Format

```python
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Response text here..."
            },
            "finish_reason": "stop",
            "index": 0
        }
    ],
    "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 100,
        "total_tokens": 150
    }
}
```

## Best Practices

??? example "Control Temperature by Use Case"

    ```python
    # Factual/analytical tasks - low temperature
    factual = unique_sdk.ChatCompletion.create(
        model="AZURE_GPT_4o_2024_1120",
        messages=[...],
        options={"temperature": 0.2}
    )

    # Creative tasks - high temperature
    creative = unique_sdk.ChatCompletion.create(
        model="AZURE_GPT_4o_2024_1120",
        messages=[...],
        options={"temperature": 0.8}
    )
    ```

## Related Resources

- [LLM Models API](llm_models.md) - Get available models
- [Search API](search.md) - Retrieve context for RAG
- [Message API](message.md) - Integrate with chat system
- [Token Utils](../sdk.md#token) - Manage token usage

