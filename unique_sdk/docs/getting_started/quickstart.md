# Quickstart Guide

Get started with the Unique Python SDK in minutes.

## Your First API Call

??? example "Search the Knowledge Base"

    ```python
    import unique_sdk

    # Configure SDK
    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."

    # Search the knowledge base
    search_results = unique_sdk.Search.create(
        user_id="user_123",
        company_id="company_456",
        searchString="What is the meaning of life?",
        searchType="VECTOR",
        limit=10
    )

    # Print results
    for result in search_results.data:
        print(f"Score: {result.score}")
        print(f"Text: {result.text}")
        print(f"Source: {result.key}")
        print("---")
    ```

??? example "Send a Chat Message"

    ```python
    # Create a message in a chat
    message = unique_sdk.Message.create(
        user_id="user_123",
        company_id="company_456",
        chatId="chat_789",
        assistantId="assistant_abc",
        text="Hello, how can you help me?",
        role="USER"
    )

    print(f"Message created: {message.id}")
    ```

??? example "Generate AI Completion"

    ```python
    # Use chat completion
    completion = unique_sdk.ChatCompletion.create(
        user_id="user_123",
        company_id="company_456",
        model="AZURE_GPT_4o_2024_1120",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain quantum computing in simple terms."},
        ],
        options={"temperature": 0.7}
    )

    print(completion.choices[0].message.content)
    ```

## Working with Content

??? example "Upload a File"

    ```python
    from unique_sdk.utils import file_io

    # Upload a PDF to the knowledge base
    content = file_io.upload_file(
        company_id="company_456",
        user_id="user_123",
        path_to_file="/path/to/document.pdf",
        displayed_filename="document.pdf",
        mime_type="application/pdf",
        scope_or_unique_path="scope_xyz123"
    )

    print(f"File uploaded: {content.id}")
    ```

??? example "Search and Download Content"

    ```python
    # Search for content
    results = unique_sdk.Content.search(
        user_id="user_123",
        company_id="company_456",
        where={
            "title": {
                "contains": "quarterly report"
            }
        }
    )

    # Download a file
    from unique_sdk.utils import file_io

    file_path = file_io.download_content(
        company_id="company_456",
        user_id="user_123",
        content_id=results.data[0].id,
        filename="downloaded_report.pdf"
    )

    print(f"File downloaded to: {file_path}")
    ```

## Using Async Operations

??? example "For better performance with multiple API calls"

    ```python
    import asyncio
    import unique_sdk

    async def batch_operations():
        # Configure SDK
        unique_sdk.api_key = "ukey_..."
        unique_sdk.app_id = "app_..."
        
        # Run multiple searches concurrently
        queries = [
            "What is AI?",
            "What is machine learning?",
            "What is deep learning?"
        ]
        
        tasks = [
            unique_sdk.Search.create_async(
                user_id="user_123",
                company_id="company_456",
                searchString=query,
                searchType="VECTOR",
                limit=5
            )
            for query in queries
        ]
        
        results = await asyncio.gather(*tasks)
        
        for i, result in enumerate(results):
            print(f"\nQuery: {queries[i]}")
            print(f"Results: {len(result.data)}")

    # Run async operations
    asyncio.run(batch_operations())
    ```

## Setting Up Webhooks

??? example "Create a webhook endpoint to receive events from Unique AI"

    ```python
    from flask import Flask, request, jsonify
    from http import HTTPStatus
    import unique_sdk

    app = Flask(__name__)

    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."
    endpoint_secret = "your_endpoint_secret"

    @app.route("/webhook", methods=["POST"])
    def webhook():
        payload = request.data
        sig_header = request.headers.get("X-Unique-Signature")
        timestamp = request.headers.get("X-Unique-Created-At")
        
        if not sig_header or not timestamp:
            return jsonify(success=False), HTTPStatus.BAD_REQUEST
        
        try:
            # Verify webhook signature
            event = unique_sdk.Webhook.construct_event(
                payload, sig_header, timestamp, endpoint_secret
            )
            
            # Handle different event types
            if event.event == "unique.chat.user-message.created":
                print(f"New message: {event.payload.text}")
                # Process the message
                
            elif event.event == "unique.chat.external-module.chosen":
                print(f"Module chosen: {event.payload.name}")
                # Handle external module selection
                
            return jsonify(success=True), HTTPStatus.OK
            
        except unique_sdk.SignatureVerificationError as e:
            print(f"Webhook signature verification failed: {e}")
            return jsonify(success=False), HTTPStatus.BAD_REQUEST

    if __name__ == "__main__":
        app.run(port=5000)
    ```

## Error Handling

??? example "Always wrap API calls in try-except blocks"

    ```python
    try:
        search = unique_sdk.Search.create(
            user_id="user_123",
            company_id="company_456",
            searchString="query",
            searchType="VECTOR"
        )
    except unique_sdk.AuthenticationError:
        print("Invalid API key or app ID")
    except unique_sdk.InvalidRequestError as e:
        print(f"Invalid request: {e.message}")
        print(f"Invalid params: {e.params}")
    except unique_sdk.APIConnectionError:
        print("Network error - check your connection")
    except unique_sdk.APIError as e:
        print(f"API error: {e.message}")
    except unique_sdk.UniqueError as e:
        print(f"Unexpected error: {e}")
    ```

    ## Using Environment Variables

    For production, use environment variables for sensitive data:

    ```python
    import os
    import unique_sdk

    # Load from environment
    unique_sdk.api_key = os.environ.get("UNIQUE_API_KEY")
    unique_sdk.app_id = os.environ.get("UNIQUE_APP_ID")

    # Or use python-dotenv
    from dotenv import load_dotenv
    load_dotenv()

    unique_sdk.api_key = os.getenv("UNIQUE_API_KEY")
    unique_sdk.app_id = os.getenv("UNIQUE_APP_ID")
    ```

Create a `.env` file:

```bash
UNIQUE_API_KEY=ukey_your_key_here
UNIQUE_APP_ID=app_your_app_id_here
UNIQUE_ENDPOINT_SECRET=your_webhook_secret
```

## Next Steps

- [Architecture Overview](../architecture.md) - Learn about SDK internals
- [API Reference](../api_resources/index.md) - Explore all available resources
