# Chat History Utility

Helper functions for managing and formatting chat conversation history for use in AI completions.

## Overview

The chat history utilities help you:

- Load and format chat history from messages
- Manage token limits for context windows
- Convert history to injectable prompt strings
- Filter system messages and format messages correctly

## Methods

??? example "`unique_sdk.utils.chat_history.load_history` - Load and format chat history"

    Loads chat history and formats it to fit within token limits for use in completions.

    **Parameters:**

    - `userId` (required) - User ID
    - `companyId` (required) - Company ID
    - `chatId` (required) - Chat ID
    - `maxTokens` (required) - Maximum tokens for the model
    - `percentOfMaxTokens` (optional) - Percentage of max tokens for history (default: 0.15 = 15%)
    - `maxMessages` (optional) - Maximum number of messages to include (default: 4)

    **Returns:**

    - `fullHistory` - Complete chat history
    - `selectedHistory` - Formatted history that fits within token limits

    **Example:**

    ```python
    from unique_sdk.utils import chat_history

    # Load history for GPT-4o (128K context)
    full_history, selected_history = chat_history.load_history(
        userId=user_id,
        companyId=company_id,
        chatId=chat_id,
        maxTokens=128000,
        percentOfMaxTokens=0.15,  # Use 15% of context for history
        maxMessages=4
    )

    # Use selected_history in your completion
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ] + selected_history + [
        {"role": "user", "content": "What did we discuss earlier?"}
    ]
    ```

    **How it works:**

    - Filters out system messages (prefixed with `[SYSTEM]`)
    - Removes the last 2 messages (usually the current exchange)
    - Selects the most recent messages that fit within token limits
    - Formats messages as `{"role": "user"|"assistant", "content": "..."}`

??? example "`unique_sdk.utils.chat_history.convert_chat_history_to_injectable_string` - Convert to prompt string"

    Converts chat history into a formatted string that can be injected into prompts.

    **Parameters:**

    - `history` (required) - List of message dictionaries with `role` and `content` keys

    **Returns:**

    - `chatHistory` - List of formatted strings
    - `chatContextTokenLength` - Token count of the formatted history

    **Example:**

    ```python
    from unique_sdk.utils import chat_history

    history = [
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."},
        {"role": "user", "content": "Tell me more."}
    ]

    history_strings, token_count = chat_history.convert_chat_history_to_injectable_string(
        history
    )

    # history_strings will be:
    # [
    #     "previous_question: What is Python?",
    #     "previous_answer: Python is a programming language.",
    #     "previous_question: Tell me more."
    # ]

    # Use in prompt
    prompt = f"""
    Previous conversation:
    {chr(10).join(history_strings)}
    
    Current question: {user_question}
    """
    ```

## Use Cases

??? example "RAG with Chat Context"

    ```python
    from unique_sdk.utils import chat_history
    import unique_sdk

    # Load recent conversation
    _, recent_history = chat_history.load_history(
        userId=user_id,
        companyId=company_id,
        chatId=chat_id,
        maxTokens=8000,
        percentOfMaxTokens=0.2,
        maxMessages=6
    )

    # Search with context
    search_results = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        searchString="project updates",
        searchType="COMBINED"
    )

    # Generate response with history
    completion = unique_sdk.ChatCompletion.create(
        user_id=user_id,
        company_id=company_id,
        model="AZURE_GPT_4o_2024_1120",
        messages=[
            {"role": "system", "content": "Answer based on search results and conversation history."}
        ] + recent_history + [
            {"role": "user", "content": "What's the latest status?"}
        ]
    )
    ```

??? example "Conversation Summarization"

    ```python
    from unique_sdk.utils import chat_history

    # Get full conversation history
    full_history, _ = chat_history.load_history(
        userId=user_id,
        companyId=company_id,
        chatId=chat_id,
        maxTokens=128000,
        percentOfMaxTokens=1.0,  # Get all history
        maxMessages=100  # Get many messages
    )

    # Convert to string for summarization
    history_strings, token_count = chat_history.convert_chat_history_to_injectable_string(
        full_history
    )

    # Summarize conversation
    summary_prompt = f"""
    Summarize this conversation:
    
    {chr(10).join(history_strings)}
    """
    ```

## Best Practices

??? example "Choose Appropriate Token Allocation"

    ```python
    # For large context models (128K+)
    _, history = chat_history.load_history(
        maxTokens=128000,
        percentOfMaxTokens=0.15,  # ~19K tokens for history
        maxMessages=10
    )

    # For smaller models (4K-8K)
    _, history = chat_history.load_history(
        maxTokens=4000,
        percentOfMaxTokens=0.2,  # ~800 tokens for history
        maxMessages=4  # Fewer messages
    )
    ```

??? example "Handle Long Conversations"

    ```python
    # For very long conversations, use smaller percentage
    _, recent_history = chat_history.load_history(
        userId=user_id,
        companyId=company_id,
        chatId=chat_id,
        maxTokens=8000,
        percentOfMaxTokens=0.1,  # Only 10% for history
        maxMessages=3  # Just last few exchanges
    )
    ```

## Related Resources

- [Message API](../api_resources/message.md) - Manage individual messages
- [ChatCompletion API](../api_resources/chat_completion.md) - Use history in completions
- [Token Management](token.md) - Count tokens in history
- [Space API](../api_resources/space.md) - Chat in spaces

