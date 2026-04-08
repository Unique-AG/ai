
# Elicitation Service - Basics

Elicitation allows your agent to request structured input from users during a conversation. The user sees a form or is directed to a URL, and their response is captured for the agent to process.

<!--
```{.python #elicitation_imports}
from unique_toolkit.elicitation import (
    ElicitationMode,
    ElicitationStatus,
    ElicitationDeclinedException,
    ElicitationCancelledException,
    ElicitationExpiredException,
)
```
-->

## Modes

| Mode | Description |
|------|-------------|
| `FORM` | Display a JSON schema-based form to the user |
| `URL` | Direct the user to an external URL |

## Creating a FORM Elicitation

The most common use case is requesting structured data via a form. The form fields are defined using a JSON schema.

```{.python #elicitation_create_form}
elicitation = chat_service.elicitation.create(
    mode=ElicitationMode.FORM,
    message="Please provide the required information",
    tool_name="data_collection",
    json_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "title": "Your Name"},
            "confirm": {"type": "boolean", "title": "I confirm"}
        },
        "required": ["name", "confirm"]
    }
)
```

The `chat_service.elicitation` property provides an `ElicitationService` automatically configured for the current chat context.

## Elicitation Statuses

| Status | Description |
|--------|-------------|
| `PENDING` | User has not yet responded |
| `ACCEPTED` | User accepted and provided data |
| `DECLINED` | User explicitly declined |
| `CANCELLED` | User cancelled the request |
| `EXPIRED` | Elicitation timed out |

## Checking Elicitation Status

After creating an elicitation, you can check its status and handle each case:

```{.python #elicitation_check_status}
result = chat_service.elicitation.get(elicitation.id)

if result.status == ElicitationStatus.PENDING:
    chat_service.modify_assistant_message(
        content="Waiting for your response..."
    )
elif result.status == ElicitationStatus.ACCEPTED:
    user_data = result.response_content
    chat_service.modify_assistant_message(
        content=f"Thank you {user_data.get('name')}!"
    )
elif result.status == ElicitationStatus.DECLINED:
    chat_service.modify_assistant_message(
        content="No problem, let me know if you change your mind."
    )
elif result.status == ElicitationStatus.CANCELLED:
    chat_service.modify_assistant_message(
        content="Request was cancelled."
    )
elif result.status == ElicitationStatus.EXPIRED:
    chat_service.modify_assistant_message(
        content="The request has expired. Please try again."
    )
```

## Waiting for Elicitation Response

Since elicitation is asynchronous, you typically need to poll until the user responds or the request expires. Here's a helper that waits for completion:

```{.python #elicitation_wait_helper}
import asyncio

async def wait_for_elicitation(
    elicitation_service,
    elicitation_id: str,
    poll_interval: float = 1.0,
    max_wait: float = 300.0,
):
    """
    Poll until elicitation is no longer PENDING or timeout is reached.
    
    Returns the final Elicitation result.
    Raises TimeoutError if max_wait is exceeded while still PENDING.
    """
    max_attempts = int(max_wait // poll_interval)
    for _ in range(max_attempts):
        result = await elicitation_service.get_async(elicitation_id)
        if result.status != ElicitationStatus.PENDING:
            return result
        await asyncio.sleep(poll_interval)
    
    raise TimeoutError("Timed out waiting for elicitation response.")
```

## Using Exceptions for Status Handling

The toolkit provides specialized exceptions with built-in agent instructions for non-success statuses. Combine this with the wait helper for clean error handling:

```{.python #elicitation_helper_function}
def handle_elicitation_result(result):
    """Process elicitation result and raise appropriate exceptions for non-success."""
    if result.status == ElicitationStatus.ACCEPTED:
        return result.response_content
    elif result.status == ElicitationStatus.PENDING:
        return None
    elif result.status == ElicitationStatus.DECLINED:
        raise ElicitationDeclinedException()
    elif result.status == ElicitationStatus.CANCELLED:
        raise ElicitationCancelledException()
    elif result.status == ElicitationStatus.EXPIRED:
        raise ElicitationExpiredException()
```

Each exception includes a default `INSTRUCTION` attribute with guidance for the agent:

```python
# Example: ElicitationDeclinedException.INSTRUCTION contains:
# "The user has declined the elicitation request. Please inform the user 
#  that you understand they chose not to provide the requested information..."
```

## Full Example

<!--
```{.python file=docs/.python_files/elicitation_basic.py}
<<common_imports>>
<<elicitation_imports>>
<<elicitation_helper_function>>
<<full_sse_setup_with_services>>
    <<elicitation_create_form>>
    <<elicitation_check_status>>
```
-->

??? example "Full Example (Click to expand)"
    
    <!--codeinclude-->
    [Basic Elicitation](../../../examples_from_docs/elicitation_basic.py)
    <!--/codeinclude-->
