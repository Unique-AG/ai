# Webhooks

Webhooks enable real-time event notifications from Unique AI to your application, allowing you to respond to user interactions and system events as they happen.

## Overview

A core functionality of Unique AI is the ability for users to engage in an interactive chat feature. SDK developers can hook into this chat to provide new functionalities.

Your App (refer to `app-id` in [Configuration](../getting_started/configuration.md)) must be subscribed to each individual Unique event in order to receive a webhook.

## Webhook Headers

Each webhook sent by Unique includes a set of headers:

```yaml
X-Unique-Id: evt_... # Event id, same as in the body.
X-Unique-Signature: ... # A HMAC-SHA256 hex signature of the entire body.
X-Unique-Version: 1.0.0 # Event payload version.
X-Unique-Created-At: 1705960141 # Unix timestamp (seconds) of the delivery time.
X-Unique-User-Id: ... # The user who initiated the message.
X-Unique-Company-Id: ... # The company to which the user belongs.
```

## Success & Retry Logic

- **Success:** Webhooks are considered successfully delivered if your endpoint returns a status code between `200` and `299`.
- **Retry:** If your endpoint returns a status code of `300` - `399`, `429`, or `500` - `599`, Unique will retry the delivery of the webhook with an exponential backoff up to five times.
- **Expired:** If your endpoint returns any other status (e.g., `404`), it is marked as expired and will not receive any further requests.

## Signature Verification

The webhook body, containing a timestamp of the delivery time, is signed with HMAC-SHA256. Always verify the signature to ensure the webhook is authentic and from Unique AI.

### Basic Verification

```python
from http import HTTPStatus
from flask import Flask, jsonify, request
import unique_sdk

endpoint_secret = "YOUR_ENDPOINT_SECRET"

@app.route("/webhook", methods=["POST"])
def webhook():
    event = None
    payload = request.data

    sig_header = request.headers.get("X-Unique-Signature")
    timestamp = request.headers.get("X-Unique-Created-At")

    if not sig_header or not timestamp:
        print("⚠️  Webhook signature or timestamp headers missing.")
        return jsonify(success=False), HTTPStatus.BAD_REQUEST

    try:
        event = unique_sdk.Webhook.construct_event(
            payload, sig_header, timestamp, endpoint_secret
        )
    except unique_sdk.SignatureVerificationError as e:
        print("⚠️  Webhook signature verification failed. " + str(e))
        return jsonify(success=False), HTTPStatus.BAD_REQUEST
    
    # Process the event
    handle_event(event)
    
    return jsonify(success=True), HTTPStatus.OK
```

### Custom Tolerance

The `construct_event` method will compare the signature and raise a `unique_sdk.SignatureVerificationError` if the signature does not match. It will also raise this error if the `createdAt` timestamp is outside of a default tolerance of 5 minutes.

Adjust the `tolerance` by passing a fifth parameter to the method (tolerance in seconds):

```python
event = unique_sdk.Webhook.construct_event(
    payload, sig_header, timestamp, endpoint_secret, 0  # No tolerance
)
```

## Available Events

### User Message Created

**Event Name:** `unique.chat.user-message.created`

This webhook is triggered for every new chat message sent by the user. This event occurs regardless of whether it is the first or a subsequent message in a chat.

**Payload Structure:**

```json
{
  "id": "evt_...",
  "version": "1.0.0",
  "event": "unique.chat.user-message.created",
  "createdAt": "1705960141",
  "userId": "...",
  "companyId": "...",
  "payload": {
    "chatId": "chat_...",
    "assistantId": "assistant_...",
    "text": "Hello, how can I help you?"
  }
}
```

**Use Cases:**

- Log user interactions
- Trigger custom workflows
- Integrate with external systems
- Monitor chat activity

**Example Handler:**

```python
def handle_user_message(event):
    """Handle new user messages."""
    user_id = event.userId
    company_id = event.companyId
    chat_id = event.payload.chatId
    text = event.payload.text
    
    print(f"New message in chat {chat_id}: {text}")
    
    # Your custom logic here
    # For example, trigger a search or process the message
```

### External Module Chosen

**Event Name:** `unique.chat.external-module.chosen`

This webhook is triggered when the Unique AI selects an external module as the best response to a user message. The module must be marked as `external` and available for the assistant used in the chat to be selected by the AI.

Unique's UI will create an empty `assistantMessage` below the user message and update this message with status updates.

**⚠️ Important:** The SDK is expected to modify this assistantMessage with its answer to the user message.

**Payload Structure:**

```json
{
  "id": "evt_...",
  "version": "1.0.0",
  "event": "unique.chat.external-module.chosen",
  "createdAt": "1705960141",
  "userId": "...",
  "companyId": "...",
  "payload": {
    "name": "example-sdk",
    "description": "Example SDK",
    "configuration": {},
    "chatid": "chat_...",
    "assistantId": "assistant_...",
    "userMessage": {
      "id": "msg_...",
      "text": "Hello World!",
      "createdAt": "2024-01-01T00:00:00.000Z"
    },
    "assistantMessage": {
      "id": "msg_...",
      "createdAt": "2024-01-01T00:00:00.000Z"
    }
  }
}
```

**Example Handler:**

```python
def handle_external_module(event):
    """Handle external module selection."""
    user_id = event.userId
    company_id = event.companyId
    chat_id = event.payload.chatid
    assistant_message_id = event.payload.assistantMessage.id
    user_text = event.payload.userMessage.text
    
    # Process the user message and generate a response
    response_text = process_user_message(user_text)
    
    # Update the assistant message with your response
    unique_sdk.Message.modify(
        user_id=user_id,
        company_id=company_id,
        id=assistant_message_id,
        chatId=chat_id,
        text=response_text,
    )
```

## Best Practices

??? example "Use Async Processing for Long Operations"

    For long-running operations, acknowledge the webhook quickly and process asynchronously:

    ```python
    @app.route("/webhook", methods=["POST"])
    def webhook():
        # Verify signature
        event = unique_sdk.Webhook.construct_event(...)
        
        # Queue for async processing
        async_queue.enqueue(process_event, event)
        
        # Return immediately
        return jsonify(success=True), HTTPStatus.OK
    ```

## Related Resources

- [Message API](api_resources/message.md) - Modify assistant messages
- [Message Log API](api_resources/message_log.md) - Update execution steps
- [Message Execution API](api_resources/message_execution.md) - Track long-running operations
- [Configuration Guide](getting_started/configuration.md) - Set up your app credentials
- [Tutorials](tutorials/folder_updates.md) - Step-by-step tutorials and guides

