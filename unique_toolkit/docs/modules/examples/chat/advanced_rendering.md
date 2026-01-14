# Advanced Rendering - Examples

This page provides practical code examples for implementing advanced rendering features in chat messages. For broader documentation and concepts, see the [Advanced Rendering Documentation](../../../chat/advanced_rendering).

## Prompt Buttons

Prompt buttons allow users to easily add follow-up prompts suggested by the agent to their prompt field.

### Basic Example

```{.python #rendering_prompt_buttons}
prompt_button_string = create_prompt_button_string(button_text="Click me", next_user_message="Next user message")
chat_service.create_assistant_message(
    content=f"Here is a prompt button:\n {prompt_button_string}",
)
```

### Full Example

<!--
```{.python file=docs/.python_files/chat_prompt_button.py}
<<full_sse_setup_with_services>>
    <<rendering_prompt_buttons>>
    <<free_user_input>>
```
-->

## LaTeX Formulas

### Using the Helper Function (Block Math)

The `create_latex_formula_string` helper function creates block math formulas:

```{.python #rendering_latex_formula}
latex_formula_string = create_latex_formula_string(
    latex_expression=r"\int_{a}^{b} f(x) \, dx"
)
chat_service.create_assistant_message(
    content=f"Here is a latex formula: {latex_formula_string}",
)
```

### Basic Formula (Manual)

To include a basic formula, wrap it in escaped square brackets:

```python
# Block math example
formula = r"\[E = mc^2\]"
chat_service.create_assistant_message(
    content=f"The famous equation: {formula}",
)
```

### Inline Math Example

For inline formulas within text, use escaped parentheses:

```python
# Inline math example
content = f"The area of a circle is \( \pi r^2 \)."
chat_service.create_assistant_message(content=content)
```

### Complex Formula Example

For more complex formulas, ensure all LaTeX syntax is correctly used within the escaped brackets:

```python
# Complex formula with inline math
content = f"The integral of a function is given by \[\int_{a}^{b} f(x) \, dx\]."
chat_service.create_assistant_message(content=content)
```

## Images

### Rendering an Uploaded Image

```{.python #rendering_image}
# Example: Rendering an image that was uploaded to the chat
# The content_id is obtained from the uploaded image
content_id = "cont_nwnfwd7kq5czq04begyb6ub8"  # Example content ID
image_markdown = f"![image](unique://content/{content_id})"
chat_service.create_assistant_message(
    content=f"This is an image that I took from a note:\n{image_markdown}",
)
```

### Getting Content ID from Uploaded Images

```python
# Download images and documents from the chat
images, documents = chat_service.download_chat_images_and_documents()

if len(images) > 0:
    # Use the first uploaded image's content ID
    content_id = images[0].id
    image_markdown = f"![image](unique://content/{content_id})"
    chat_service.create_assistant_message(
        content=f"Here's the image you uploaded:\n{image_markdown}",
    )
```

## Financial Chart

### Basic Financial Chart Example

```{.python #rendering_financial_chart}
import json
from datetime import datetime, timezone

# Example: Creating a financial chart payload
financial_data = [
    {
        "info": {
            "companyName": "Apple",
            "instrumentName": "Apple Rg",
            "ticker": "AAPL",
            "exchange": "NASDAQ",
            "currency": "USD"
        },
        "priceHistory": [
            {"date": "2025-01-02", "value": 243.85},
            {"date": "2025-01-03", "value": 245.12},
            {"date": "2025-01-04", "value": 244.50},
            {"date": "2025-01-05", "value": 246.20},
            # ... more price history entries
        ],
        "metrics": [
            {
                "name": "Open",
                "value": 221.45,
                "timestamp": "2025-03-27T09:30:01-04:00"
            },
            {
                "name": "High",
                "value": 225.30,
                "timestamp": "2025-03-27T09:30:01-04:00"
            },
            {
                "name": "Close",
                "value": 223.10,
                "timestamp": "2025-03-27T09:30:01-04:00"
            },
            # ... more metrics
        ],
        "lastUpdated": "2025-03-28T16:10:09.243846",
        "version": 1
    }
]

# Format as financialchart code block
financial_chart_markdown = f"```financialchart\n{json.dumps(financial_data, indent=2)}\n```"

chat_service.create_assistant_message(
    content=f"Here is the stock performance:\n{financial_chart_markdown}",
)
```

### Comparative View Example

To show multiple instruments for comparison:

```python
import json

# Multiple instruments for comparative view
financial_data = [
    {
        "info": {
            "companyName": "Apple",
            "instrumentName": "Apple Rg",
            "ticker": "AAPL",
            "exchange": "NASDAQ",
            "currency": "USD"
        },
        "priceHistory": [
            {"date": "2025-01-02", "value": 243.85},
            {"date": "2025-01-03", "value": 245.12},
            # ... more entries
        ],
        "metrics": [
            {"name": "Open", "value": 221.45, "timestamp": "2025-03-27T09:30:01-04:00"},
            # ... more metrics
        ],
        "lastUpdated": "2025-03-28T16:10:09.243846",
        "version": 1
    },
    {
        "info": {
            "companyName": "Microsoft",
            "instrumentName": "Microsoft Corp",
            "ticker": "MSFT",
            "exchange": "NASDAQ",
            "currency": "USD"
        },
        "priceHistory": [
            {"date": "2025-01-02", "value": 415.20},
            {"date": "2025-01-03", "value": 417.50},
            # ... more entries
        ],
        "metrics": [
            {"name": "Open", "value": 410.00, "timestamp": "2025-03-27T09:30:01-04:00"},
            # ... more metrics
        ],
        "lastUpdated": "2025-03-28T16:10:09.243846",
        "version": 1
    }
]

financial_chart_markdown = f"```financialchart\n{json.dumps(financial_data, indent=2)}\n```"

chat_service.create_assistant_message(
    content=f"Here is a comparison of stock performance:\n{financial_chart_markdown}",
)
```

## Full Examples
??? example "Full Examples Rendering (Click to expand)"
    
    <!--codeinclude-->
    [Button](../../../examples_from_docs/chat_prompt_button.py)
    [Latex](../../../examples_from_docs/chat_latex_formula.py)
    <!--/codeinclude-->


