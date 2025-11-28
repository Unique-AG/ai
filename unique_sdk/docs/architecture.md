# SDK Architecture

This document provides an overview of the Unique Python SDK architecture, design patterns, and core components.

## Overview

The Unique Python SDK is designed to provide seamless access to the Unique AI platform's REST API. It follows a resource-oriented architecture inspired by the Stripe SDK, making it intuitive for developers familiar with modern API clients.

## Core Components

### 1. API Resources

API Resources are the primary interface for interacting with the Unique AI platform. Each resource corresponds to a specific entity or functionality in the API.

**Key Resources:**

- **[Content](api_resources/content.md)**: Manage knowledge base documents
- **[Message](api_resources/message.md)**: Handle chat messages and interactions
- **[Search](api_resources/search.md)**: Perform vector and full-text searches
- **[SearchString](api_resources/search_string.md)**: Transform and optimize search queries
- **[ChatCompletion](api_resources/chat_completion.md)**: Generate AI completions
- **[Embeddings](api_resources/embeddings.md)**: Generate vector embeddings
- **[Space](api_resources/space.md)**: Manage conversational spaces
- **[Folder](api_resources/folder.md)**: Organize knowledge base content
- **[User](api_resources/user.md) & [Group](api_resources/group.md)**: Manage users and permissions
- **[AgenticTable](api_resources/agentic_table.md)**: Work with AI-powered tables
- **[ShortTermMemory](api_resources/short_term_memory.md)**: Store temporary conversation data
- **[MessageAssessment](api_resources/message_assessment.md)**: Evaluate message quality
- **[MessageExecution](api_resources/message_execution.md)**: Track long-running operations
- **[MessageLog](api_resources/message_log.md)**: Log message processing steps
- **[LLMModels](api_resources/llm_models.md)**: Get available AI models

### 2. Webhook System

The webhook system provides secure, event-driven communication from the Unique platform to your application with HMAC-SHA256 signature verification.

### 3. Utility Functions

The SDK includes utility modules for:

- Token management and counting
- File I/O operations
- Chat history management
- Source processing and formatting

## Design Patterns

### Resource-Oriented Design

Each API endpoint is represented as a resource class with standardized CRUD operations.

### Async/Sync Duality

Most operations have both synchronous and asynchronous versions:

```python
# Synchronous
message = unique_sdk.Message.create(user_id, company_id, **params)

# Asynchronous
message = await unique_sdk.Message.create_async(user_id, company_id, **params)
```

### Automatic Retry with Exponential Backoff

Transient errors are automatically retried with increasing delays (3 retries with 2x backoff factor).

## Error Hierarchy

The SDK uses a structured error hierarchy:

- **`APIError`**: Base class for all API errors
- **`InvalidRequestError`**: Client-side validation errors (400)
- **`AuthenticationError`**: Authentication failures (401)
- **`PermissionError`**: Authorization failures (403)
- **`NotFoundError`**: Resource not found (404)
- **`RateLimitError`**: Rate limit exceeded (429)
- **`ServerError`**: Server-side errors (500+)

## Security

- **HMAC-SHA256** signature verification for webhooks
- **API Key** authentication for all requests
- **Secure credential storage** via environment variables

## Performance

- **Connection pooling** for efficient HTTP requests
- **Automatic retry** with exponential backoff
- **Async support** for concurrent operations
- **Bulk operations** where available

## Next Steps

Now that you understand the SDK architecture:

1. **[Get Started](getting_started/installation.md)** - Install and configure the SDK
2. **[Try the Quickstart](getting_started/quickstart.md)** - Make your first API call
3. **[Explore API Resources](api_resources/index.md)** - Browse all available APIs
4. **[See Tutorials](tutorials/folder_updates.md)** - Learn from step-by-step tutorials
5. **[Read the Full Documentation](../sdk.md)** - Complete API reference
