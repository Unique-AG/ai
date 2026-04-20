# Lifecycle and Concurrency

## Stream Lifecycle

```mermaid
flowchart TB
    subgraph S1["1. SETUP"]
        S1A["pipeline.reset()<br/>Clear previous state"]
        S1B["bus.publish(StreamStarted)<br/>content_chunks attached"]
        S1A --> S1B
    end

    subgraph S2["2. STREAMING"]
        S2A["async for event in stream:"]
        S2B["flushed = pipeline.on_event(event)"]
        S2C["if flushed:<br/>bus.publish(TextDelta)"]
        S2A --> S2B --> S2C --> S2A
    end

    subgraph S3["3. FINALIZE (finally block)"]
        S3A["pipeline.on_stream_end()<br/>→ residual flush flag"]
        S3B["if flushed:<br/>bus.publish(TextDelta)"]
        S3C["bus.publish(StreamEnded)"]
        S3A --> S3B --> S3C
    end

    subgraph S4["4. RESULT"]
        S4A["pipeline.build_result()<br/>Assemble response"]
    end

    S1 --> S2 --> S3 --> S4
```

The default `MessagePersistingSubscriber` translates each published event into a single
`unique_sdk.Message.modify_async` call (see [SDK Integration Timing](#sdk-integration-timing)).

## State Management

### Handler State

Each handler maintains private state:

| Handler | State |
|---------|-------|
| TextDeltaHandler / ChatCompletionTextHandler | `_state: TextState`, replacer buffers |
| ToolCallHandler | `_function_name_by_item_id`, `_tool_calls` |
| CompletedHandler | `_usage`, `_output` |
| CodeInterpreterHandler | `_message_logs`, `_code` |

### Subscriber State

| Subscriber | State |
|------------|-------|
| `MessagePersistingSubscriber` | `_chunks_by_message: dict[str, list[ContentChunk]]` — per-stream retrieved chunks, seeded on `StreamStarted` and cleared on `StreamEnded` so overlapping streams stay isolated |

### Reset Protocol

`reset()` clears all per-run handler state:

```python
def reset(self) -> None:
    self._state = TextState(full_text="", original_text="")
    for replacer in self._replacers:
        replacer.flush()  # Discard buffered data
```

### Flush Protocol

Text handlers' `on_stream_end()` cascade-flushes replacers and reports residual state via `bool`:

```python
async def on_stream_end(self) -> bool:
    remaining = ""
    for replacer in self._replacers:
        if remaining:
            remaining = replacer.process(remaining)
        remaining += replacer.flush()

    if remaining:
        self._state.full_text += remaining
        return True
    return False
```

The orchestrator uses that flag to publish one final `TextDelta` before `StreamEnded`:

```python
flushed = await self._pipeline.on_stream_end()
if flushed:
    await self._publish_text_delta(message_id, chat_id)
await self._bus.publish_and_wait_async(StreamEnded(...))
```

## Concurrency Rules

| Rule | Enforcement |
|------|-------------|
| Sequential reuse is safe | `reset()` before each run |
| No concurrent sharing of a pipeline | One pipeline instance per in-flight stream |
| Subscriber may be shared across streams | `MessagePersistingSubscriber` keys chunks by `message_id`; concurrent streams with distinct message IDs do not interfere |
| Connection errors are handled | `httpx.RemoteProtocolError` caught; `StreamEnded` still fires from the `finally` block |

### Why No Concurrent Pipeline Sharing?

Handlers are stateful:

- Text handler accumulates text in `_state`
- Replacers buffer partial matches
- Tool handler tracks item IDs

Concurrent access would corrupt these buffers.

### Pattern: One Pipeline Per Stream

```python
# CORRECT: Pipeline per request
async def handle_request(event):
    pipeline = build_pipeline()  # Fresh instance (no settings needed)
    handler = ResponsesCompleteWithReferences(settings, pipeline=pipeline)
    return await handler.complete_with_references_async(...)

# INCORRECT: Shared pipeline across concurrent requests
shared_pipeline = build_pipeline()  # BAD for concurrency

async def handle_request(event):
    handler = ResponsesCompleteWithReferences(settings, pipeline=shared_pipeline)
    return await handler.complete_with_references_async(...)  # Concurrent corruption!
```

## Error Handling

### Mid-Stream Connection Drop

```python
try:
    async for event in stream:
        flushed = await self._pipeline.on_event(event)
        if flushed:
            await self._publish_text_delta(message_id, chat_id)
except httpx.RemoteProtocolError as exc:
    _LOGGER.warning(
        "Stream connection closed prematurely. "
        "Finalizing with content received so far. Error: %s",
        exc,
    )
finally:
    flushed = await self._pipeline.on_stream_end()
    if flushed:
        await self._publish_text_delta(message_id, chat_id)
    await self._bus.publish_and_wait_async(StreamEnded(..., full_text=..., original_text=...))
```

`StreamEnded` always fires from the `finally` block, so the persister always records
`stoppedStreamingAt` / `completedAt` — even on partial streams.

### Validation Errors

Chat context must be set:

```python
chat = settings.context.chat
if chat is None:
    raise ValueError("Chat context is not set")
```

## SDK Integration Timing

Subscribers (not handlers) talk to the SDK. With the default subscribers:

| Phase | Event published | Subscriber | SDK call |
|-------|----------------|-----------|----------|
| Before stream | `StreamStarted` | `MessagePersistingSubscriber` | `Message.modify_async` (`references=[]`, `startedStreamingAt=…`) |
| During stream (per text flush) | `TextDelta` | `MessagePersistingSubscriber` | `Message.modify_async` (`text`, `originalText`, filtered `references`) |
| During stream (per tool-activity state change) | `ActivityProgress` | `ProgressLogPersister` | `MessageLog.create_async` on first sighting, `MessageLog.update_async` on transitions (keyed by `correlation_id`) |
| After stream | `StreamEnded` | `MessagePersistingSubscriber` | `Message.modify_async` (`text + "".join(appendices)`, `references`, `stoppedStreamingAt`, `completedAt`) |

`StreamEnded.appendices` carries blocks contributed by auxiliary handlers (e.g. the code
interpreter's executed-code block) so the final persist stays a single `Message.modify_async`
call — no `retrieve` + `modify` round-trip needed.

Throttling is controlled by the **text handler** (`send_every_n_events` on the Chat Completions handler);
the bus itself does not throttle. To add rate-limiting, wrap the subscriber or add a throttling
subscriber that forwards a reduced-rate event stream to the persister.

## Custom Wiring

The bus itself is owned by the orchestrator and cannot be injected; instead, callers
supply the desired subscribers at construction time (or attach more later via the `bus`
property):

```python
orchestrator = ChatCompletionsCompleteWithReferences(
    settings,
    pipeline=pipeline,
    subscribers=[
        my_tracing_subscriber,
        MessagePersistingSubscriber(settings).handle,
    ],
)
```

When `subscribers=` is omitted, the orchestrator registers the defaults automatically —
for `ChatCompletionsCompleteWithReferences` that is `MessagePersistingSubscriber(settings)`;
for `ResponsesCompleteWithReferences` it is both `MessagePersistingSubscriber(settings)` **and**
`ProgressLogPersister(settings)` (since the Responses API publishes `ActivityProgress` for
code interpreter calls). Passing an explicit iterable (including `[]`) is treated as the caller
having fully specified the subscriber set — the defaults are **not** added.
