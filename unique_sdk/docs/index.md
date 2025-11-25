# Welcome to Unique SDK

Unique SDK enables Python developers to access the Unique platform through its public API endpoints, facilitating development of custom integrations, tools, and agents.

## Table of Contents

### Environment Setup

- [Installation](getting_started/installation.md) - Install and set up the SDK
- [Configuration](getting_started/configuration.md) - Configure API credentials and settings

### Application Types

- [Quickstart Guide](getting_started/quickstart.md) - Get started with your first API calls

#### Standalone Application

Standalone applications use the capabilities of the Unique platform but do not interact with users directly via any GUI. Examples include:

- Knowledge base management pipelines
- Automatic report generation
- Batch processing workflows

See the [Quickstart Guide](getting_started/quickstart.md) for examples of standalone applications.

#### Event Driven Applications

Event-driven applications react to events obtained from the Unique platform. These events can be used to initialize services that interact with the chat, knowledge base, or other platform features.

- [Webhooks](webhooks.md) - Receive and handle real-time events from Unique AI
- [Tutorials](tutorials/folder_updates.md) - Step-by-step tutorials and guides

### Supported Models

- [LLM Models](api_resources/llm_models.md) - View available language models for chat completions and other operations

### API Reference

The SDK provides access to the following API resources:

#### Core Resources

- [Content](api_resources/content.md) - Manage knowledge base content and documents
- [Message](api_resources/message.md) - Create and manage chat messages
- [Search](api_resources/search.md) - Search the knowledge base
- [Search String](api_resources/search_string.md) - String-based search operations
- [Folder](api_resources/folder.md) - Organize content in folders
- [Space](api_resources/space.md) - Manage conversational spaces and assistants

#### Advanced Features

- [Chat Completion](api_resources/chat_completion.md) - Generate chat completions using LLMs
- [Embeddings](api_resources/embeddings.md) - Generate embeddings for text
- [Short Term Memory](api_resources/short_term_memory.md) - Store temporary data between chat rounds
- [Agentic Table](api_resources/agentic_table.md) - Interact with agentic tables

#### Message Management

- [Message Log](api_resources/message_log.md) - Update execution steps in chat UI
- [Message Execution](api_resources/message_execution.md) - Track long-running message operations
- [Message Assessment](api_resources/message_assessment.md) - Evaluate message quality and compliance

#### User & Access Management

- [User](api_resources/user.md) - Manage users and user configurations
- [Group](api_resources/group.md) - Manage user groups and permissions

#### Utilities

- [Chat History](utilities/chat_history.md) - Load and convert chat history
- [File I/O](utilities/file_io.md) - Upload and download files
- [Sources](utilities/sources.md) - Process and merge search sources
- [Token Management](utilities/token.md) - Manage token usage and limits
- [Chat in Space](utilities/chat_in_space.md) - Helper functions for space interactions

### Query Language

- [UniqueQL](uniqueql.md) - Advanced query language for filtering metadata

### Architecture & Tutorials

- [Architecture Overview](architecture.md) - Understand the SDK's architecture and design
- [Tutorials](tutorials/folder_updates.md) - Step-by-step tutorials:
  - [Folder Updates](tutorials/folder_updates.md) - Manage folder configurations and access
  - [Rule-Based Search](tutorials/get_contents.md) - Search content using metadata filters
  - [OpenAI Integration](tutorials/openai_scripts.md) - Use OpenAI SDK with Unique API proxy

## Next Steps

1. **New to Unique SDK?** Start with the [Installation Guide](getting_started/installation.md)
2. **Ready to code?** Follow the [Quickstart Guide](getting_started/quickstart.md)
3. **Want to learn?** Check out our [Tutorials](tutorials/folder_updates.md) for step-by-step guides
4. **Building integrations?** Check out [Webhooks](webhooks.md) for event-driven applications
5. **Need help?** Browse the [API Reference](#api-reference) for detailed documentation

