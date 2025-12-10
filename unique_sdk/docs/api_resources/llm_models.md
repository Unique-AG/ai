# LLM Models API

The LLM Models API retrieves available language models for use with Unique AI.

## Overview

Get the list of AI models available for chat completions and other operations.

## Methods

??? example "`unique_sdk.LLMModels.get_models` - Get available models"

    !!! info "Compatibility"
        Compatible with release >.46

    Get available LLM models, optionally filtered by module.

    **Parameters:**

    - `module` (str | None, optional) - Filter by module (currently only `"UNIQUE_AI"` supported)

    **Returns:**

    Returns a [`LLMModels.LLMModelsResponse`](#llmmodelsllmmodelsresponse) object.

    **Example:**

    ```python
    models = unique_sdk.LLMModels.get_models(
        user_id=user_id,
        company_id=company_id,
        module="UNIQUE_AI"
    )

    for model_id in models.models:
        print(f"Model: {model_id}")
    ```

    **Example - List All Models:**

    ```python
    models = unique_sdk.LLMModels.get_models(
        user_id=user_id,
        company_id=company_id
    )

    # Print all available model IDs
    for model_id in models.models:
        print(f"Model ID: {model_id}")
    ```

## Use Cases

??? example "Model Availability Check"

    ```python
    def is_model_available(model_name):
        """Check if a specific model is available."""
        
        models = unique_sdk.LLMModels.get_models(
            user_id=user_id,
            company_id=company_id
        )
        
        return model_name in models.models

    # Check before using
    if is_model_available("AZURE_GPT_4o_2024_1120"):
        # Use the model
        completion = unique_sdk.ChatCompletion.create(
            model="AZURE_GPT_4o_2024_1120",
            ...
        )
    else:
        # Fallback to another model
        print("Model not available, using fallback")
    ```

## Return Types

#### LLMModels.LLMModelsResponse {#llmmodelsllmmodelsresponse}

??? note "The `LLMModels.LLMModelsResponse` object contains a list of available model IDs"

    **Fields:**

    - `models` (List[str]) - List of available model identifier strings

    **Returned by:** `LLMModels.get_models()`

## Related Resources

- [ChatCompletion API](chat_completion.md) - Use models for completions
- [Token Management](../utilities/token.md) - Manage token usage

