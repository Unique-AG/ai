# API Reference

This is the API Reference for the unique toolkit.

## Available Modules

### Core Services

- [Chat Module](./modules/chat.md) - All capabilities to interact with the chat frontend
- [Knowledge Base Module](./modules/knowledge_base.md) - All interaction with the knowledge base
- [Short Term Memory Module](./modules/short_term_memory.md) - Create memories attached to a specific chat
- [App Module](./modules/app.md) - App initialization, SDK setup, event handling, and webhook verification
- [Smart Rules](./modules/content_smart_rules.md) - Create complex queries using UniqueQL to filter and search content

### Framework Utilities

- [OpenAI Client](./modules/openai.md) - OpenAI-compatible client for the toolkit platform
- [Langchain Client](./modules/langchain.md) - Langchain integration client

### Deprecated Modules

- [Content Module (Deprecated)](./modules/content.md) - Low-level content operations (use KnowledgeBaseService instead)
- [Embedding Module (Deprecated soon)](./modules/embedding.md) - Embedding functionality (use OpenAI Client directly)
- [Language Model Module (Deprecated soon)](./modules/language_model.md) - Language model operations (use OpenAI Client directly)
