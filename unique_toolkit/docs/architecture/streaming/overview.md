# Overview: Streaming Pipeline Design

## Problem

LLM providers emit tokens incrementally. The toolkit must:

1. Display text to users in real-time (via Unique SDK)
2. Normalise citation patterns across chunk boundaries
3. Assemble a typed response for downstream code
4. Support multiple wire formats (Responses API, Chat Completions, future sources)

## Solution: Handler Pipeline

The architecture separates **stream consumption** from **event processing**:

```mermaid
flowchart TB
    CWR["CompleteWithReferences<br/>(entry point)"]
    SP["StreamPipeline<br/>(routes events by type)"]
    TH["Text Handler"]
    TOH["Tool Handler"]
    CH["Completed Handler"]
    CIH["CodeInterpreter Handler"]
    REP["Replacers<br/>(text transformation chain)"]

    CWR -->|event| SP
    SP --> TH
    SP --> TOH
    SP --> CH
    SP --> CIH
    TH --> REP
```

### Entry Point (`CompleteWithReferences`)

- Opens the stream from OpenAI proxy
- Runs its own `async for` loop (not a shared generic runner)
- Catches `httpx.RemoteProtocolError` for graceful partial-stream handling
- Calls `pipeline.reset()` before each run
- Calls `pipeline.on_stream_end()` in finally block

### Pipeline (`StreamPipeline`)

- Routes events to typed handlers via `isinstance` checks
- Unknown events are ignored (forward compatibility)
- Collects handler outputs via `build_result()`

### Handlers

Small, focused classes that:
- Process one event type
- Maintain private state (reset between runs)
- Implement `StreamHandlerProtocol` for lifecycle

## Data Flow

```mermaid
flowchart TB
    PROXY["OpenAI Proxy"] --> EVENTS["Stream Events"]

    EVENTS --> TH["Text Handler<br/>• Replacers<br/>• SDK update<br/>• TextState"]
    EVENTS --> TOH["Tool Handler<br/>• Accumulate tool calls"]
    EVENTS --> CH["Completed Handler<br/>• Usage stats<br/>• Output items"]

    TH --> BR["build_result()"]
    TOH --> BR
    CH --> BR

    BR --> RESULT["ChatMessage +<br/>tool_calls +<br/>usage"]
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Protocols over ABCs | Structural typing; easy fakes in tests |
| Explicit `reset()` | Sequential reuse without state leakage |
| Typed dispatch via `isinstance` | Forward compatible; unknown events ignored |
| Own `async for` loop per entry point | Can catch and handle mid-stream errors |
| Replacer chain in text handler | Extensible text transformation |
