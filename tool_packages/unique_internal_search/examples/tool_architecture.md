# InternalSearch Tool Architecture

```mermaid
flowchart TD
    subgraph consumers["Consumer Layer"]
        t1["InternalSearchTool v2\nTool[InternalSearchConfig]"]
        t2["EarningCallsInternalSearchTool\nTool[EarningCallsConfig]"]
        t3["MCP Server\ncreate_unique_mcp_server()"]
    end

    subgraph service["Service Layer"]
        cfg["InternalSearchServiceConfig\n(flags + limits)"]
        svc["InternalSearchService\n(BaseService)"]
        deps["InternalSearchDeps\n· ChunkRelevancySorter\n· KnowledgeBaseService\n· ChatService | None"]
        result["InternalSearchResult\n(chunks, metadata)"]

        cfg --> svc
        deps --> svc
        svc --> result
    end

    t1 -->|holds via composition| svc
    t2 -->|holds via composition| svc
    t3 -->|holds via composition| svc

    t2 -. "state.metadata_filter_override\n(no private mutation)" .-> svc
```

## Key design principles

| Pattern | ✅ Do | ❌ Don't |
|---|---|---|
| Reuse | Compose `InternalSearchService` | Inherit `InternalSearchTool` |
| Customisation | `InternalSearchState(metadata_filter_override=…)` | `self.content_service._metadata_filter = …` |
| MCP swap | Replace consumer only | Rewrite service logic |
| Chat context | `ChatService.from_context(context)` | Call low-level functions directly |
