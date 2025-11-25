# Token Management Utility

Helper functions for counting tokens and managing token limits in AI completions.

## Overview

The Token utilities help you:
- Count tokens in text strings
- Select search results that fit within token limits
- Manage context window sizes
- Optimize token usage for completions

## Methods

??? example "`unique_sdk.utils.token.count_tokens` - Count tokens in text"

    Counts the number of tokens in a text string using tiktoken encoding.

    **Parameters:**

    - `text` (required) - Text string to count tokens for
    - `encoding_model` (optional) - Encoding model to use (default: `"cl100k_base"`)

    **Returns:**

    - `int` - Number of tokens in the text

    **Example:**

    ```python
    from unique_sdk.utils.token import count_tokens

    text = "Hello, how are you today?"
    token_count = count_tokens(text)
    print(f"Tokens: {token_count}")  # Output: Tokens: 6
    ```

    **Example - Count Multiple Texts:**

    ```python
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."}
    ]

    total_tokens = sum(
        count_tokens(msg["content"]) 
        for msg in messages
    )
    print(f"Total tokens: {total_tokens}")
    ```

??? example "`unique_sdk.utils.token.pick_search_results_for_token_window` - Select results within token limit"

    Selects search results that fit within a specified token limit.

    **Parameters:**

    - `searchResults` (required) - List of search result objects with `text` field
    - `tokenLimit` (required) - Maximum number of tokens to include
    - `encoding_model` (optional) - Encoding model (default: `"cl100k_base"`)

    **Returns:**

    - List of search result objects that fit within the token limit

    **Example:**

    ```python
    from unique_sdk.utils.token import pick_search_results_for_token_window
    import unique_sdk

    # Perform search
    search = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString="project documentation",
        searchType="COMBINED",
        limit=50  # Get more than needed
    )

    # Select results that fit in 4000 tokens
    selected_results = pick_search_results_for_token_window(
        search["data"],
        tokenLimit=4000
    )

    print(f"Selected {len(selected_results)} results")
    ```

## Use Cases

??? example "Optimize Context Window Usage"

    ```python
    from unique_sdk.utils.token import count_tokens, pick_search_results_for_token_window

    def build_optimized_context(query, max_context_tokens=4000):
        """Build context that fits within token limit."""
        
        # Search
        search = unique_sdk.Search.create(
            user_id=user_id,
            company_id=company_id,
            searchString=query,
            searchType="COMBINED",
            limit=100  # Get many results
        )
        
        # Select best results that fit
        context = pick_search_results_for_token_window(
            search["data"],
            tokenLimit=max_context_tokens
        )
        
        return context
    ```

??? example "Monitor Token Usage"

    ```python
    from unique_sdk.utils.token import count_tokens

    def check_token_usage(messages, max_tokens):
        """Check if messages fit within token limit."""
        total = sum(count_tokens(msg["content"]) for msg in messages)
        
        if total > max_tokens:
            print(f"Warning: {total} tokens exceeds limit of {max_tokens}")
            return False
        
        print(f"Using {total}/{max_tokens} tokens ({total/max_tokens*100:.1f}%)")
        return True

    messages = [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ]
    
    check_token_usage(messages, max_tokens=8000)
    ```

## Best Practices

??? example "Reserve Tokens for Response"

    ```python
    # Always reserve tokens for the AI response
    max_tokens = 8000
    response_reserve = 1000  # Reserve for response
    
    available_for_context = max_tokens - response_reserve
    
    context = pick_search_results_for_token_window(
        search["data"],
        tokenLimit=available_for_context
    )
    ```

??? example "Combine with Source Processing"

    ```python
    from unique_sdk.utils.sources import merge_sources, sort_sources
    from unique_sdk.utils.token import pick_search_results_for_token_window

    # 1. Process sources first
    merged = merge_sources(search["data"])
    sorted_results = sort_sources(merged)

    # 2. Then select by token limit
    context = pick_search_results_for_token_window(
        sorted_results,
        tokenLimit=4000
    )
    ```

## Related Resources

- [ChatCompletion API](../api_resources/chat_completion.md) - Use tokens in completions
- [Chat History](chat_history.md) - Manage history tokens
- [Sources](sources.md) - Process search results before token selection
- [LLM Models API](../api_resources/llm_models.md) - Get model context windows

