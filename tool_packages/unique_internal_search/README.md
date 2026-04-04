# Internal Search Tool

Internal Search Tool to find documents in the Knowledge Base.

## Architecture

The service is built on a mixin-based `BaseService` pattern. See `unique_internal_search/base_service.py` and `unique_internal_search/service_v2.py`.

## Chat scoping

How `chat_id`, `chat_only`, and `metadata_filter` are resolved before each search call:

```mermaid
flowchart TD
    Event["ChatEvent\n(from platform)"]

    Event --> ChatContext["ChatContext.from_chat_event()\n─────────────────\nchat_id\nassistant_id\nmetadata_filter\nparent_chat_id (if correlation)"]

    ChatContext --> UniqueContext["UniqueContext\n─────────────────\nauth → company_id, user_id\nchat → ChatContext (or None if chatless)"]

    UniqueContext -->|"bind_settings()"| Service["InternalSearchService"]

    ToolCall["ToolCall\n(from LLM)"] -->|"Tool builds state\nfrom config defaults\n+ call arguments"| State["InternalSearchState\n─────────────────\nsearch_queries\nchat_only ← config.chat_only or tool_call arg\nmetadata_filter_override ← UNSET or explicit\nlanguage_model_max_input_tokens\ncontent_ids"]

    State -->|"service.state = ..."| Service

    Service --> EffectiveChatId["_effective_chat_id\n─────────────────────────────\nexclude_uploaded_files? → None\ncontext.chat is None? → None\nparent_chat_id set? → parent_chat_id\nelse → chat_id"]

    Service --> EffectiveFilter["_effective_metadata_filter\n─────────────────────────────\nstate.metadata_filter_override is not UNSET? → override\ncontext.chat exists? → chat.metadata_filter\nelse → None"]

    EffectiveChatId --> ResolveScope
    EffectiveFilter --> ResolveScope

    Service --> ResolveScope["_resolve_search_scope()\n─────────────────────────────\nchat_only = state.chat_only\nscope_to_chat_on_upload=True?\n  → search_contents_async(ownerId=chat_id)\n  → chat_only=True if files found\nmetadata_filter = None if chat_only\n             else _effective_metadata_filter"]

    ResolveScope --> SearchFn["search_content_chunks_async()\n─────────────────────────────\ncompany_id, user_id ← auth\nchat_id ← _effective_chat_id or ''\nchat_only ← resolved\nmetadata_filter ← resolved\nscope_ids ← config.scope_ids"]

    SearchFn --> Result["list[ContentChunk]"]

    style EffectiveChatId fill:#e8f4e8
    style EffectiveFilter fill:#e8f4e8
    style ResolveScope fill:#f5f0dc
    style SearchFn fill:#dce8f5
```
