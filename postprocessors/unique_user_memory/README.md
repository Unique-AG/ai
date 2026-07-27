# Unique User Memory

Persistent per-user memory for Unique AI agents.

`unique_user_memory` stores a compact Markdown profile for each user and updates it after every agent turn. The profile is loaded before the next turn so the assistant can remember stable user context such as communication preferences, work context, expertise, recent topics, and concrete future tasks.

## What It Does

The package provides:

- `UserMemoryConfig` - Pydantic configuration for the consolidation model, profile token budget, and memory folder.
- `load_user_memory(...)` - resolves the user's private memory folder, downloads `memory.md`, and enforces the configured token budget. The `language_model` argument is used to tokenize `memory.md` when capping it, so it must be the same effective model the postprocessor uses for consolidation (see Integration below). Returns a `UserMemoryState` with the profile text and scope id.
- `UserMemoryMessageLogger` - emits chat Steps (MessageLogs) for load and update, including typed `UserMemory` detail entries the chat frontend renders as a badge that opens Settings → Context Memory. Frontends that do not know the entry type render nothing, so the entries are safe to emit in any deploy order.
- `UserMemoryPostprocessor` - runs after the assistant response, consolidates the latest turn into the profile, and uploads the updated `memory.md`.

The memory file is intentionally small and structured. It is rewritten as a full Markdown profile rather than appended to as an event log.

## Lifecycle

1. The orchestrator enables memory when `space.allow_user_memory` is true.
2. The orchestrator emits a **Loading context memory** Step, then `load_user_memory(...)` resolves the pre-provisioned root folder, ensures a private child folder for the current user, and downloads `/user-memory/<user_id>/memory.md` if it exists.
3. When load returns a `UserMemoryState`, that Step is completed with a **Context memory** detail entry (`type: UserMemory`) that the chat frontend renders as a badge opening Settings → Context Memory. A successful `None` return (soft skip) completes the Step without the entry; a raised exception marks the Step failed.
4. If memory was loaded, its text is passed into the agent context for the current turn.
5. `UserMemoryPostprocessor` runs after the assistant response.
6. The package asks the configured language model to either return `NOOP` or a complete rewritten profile.
7. If a rewrite runs, an **Updating your memory** Step is shown while consolidating (no settings entry yet).
8. If the profile changed and `memory.md` uploads successfully (ingestion skipped, content hidden from chat), that Step is completed with a **Review your context memory** detail entry (same settings badge). On NOOP or failed upload the Step completes without the entry.

## Storage Model

Memory is stored in Unique content as Markdown:

```text
/<root_folder>/<user_id>/memory.md
```

By default, `root_folder` is `user-memory`. The root folder must already exist. The package creates the per-user child folder when needed.

## Profile Format

Profiles contain YAML frontmatter followed by fixed Markdown sections:

```markdown
---
user_id: user_123
schema_version: 1
last_updated: 2026-06-17T12:00:00+00:00
turn_count: 1
---

# User Memory

## Identity
_(empty)_

## Communication Preferences
- Prefers concise answers with concrete examples.

## Work Context
_(empty)_

## Skills & Expertise
_(empty)_

## Recent Topics
_(empty)_

## Follow-ups
_(empty)_
```

The consolidation prompt preserves the schema, keeps bullets short, and returns `NOOP` when a turn has no durable user facts.

## Configuration

Memory is activated by the orchestrator when `space.allow_user_memory` is true. `UserMemoryConfig` only configures how active memory is consolidated and stored.

```python
from unique_user_memory import UserMemoryConfig

config = UserMemoryConfig(
    max_tokens=2000,
    root_folder="user-memory",
)
```

| Field | Default | Description |
| --- | --- | --- |
| `use_orchestrator_language_model` | `True` | When true, consolidation and load-time token capping use the model the orchestrator passes in and `language_model` is ignored. Set to `False` to use the configured `language_model` for both. |
| `language_model` | `DEFAULT_GPT_4o` | Model used to consolidate the latest turn and to tokenize `memory.md` at load time when `use_orchestrator_language_model` is `False`. |
| `max_tokens` | `2000` | Maximum profile size. Must be between 500 and 8000 tokens. |
| `root_folder` | `user-memory` | Root KB folder that contains per-user memory folders. |

## Integration

Typical orchestration code loads memory before the agent loop and registers the postprocessor for the same turn.

`load_user_memory` and `UserMemoryPostprocessor` must be given the **same** effective language model: the postprocessor consolidates memory with either the orchestrator model or the configured one depending on `use_orchestrator_language_model`, and load-time token capping must use that same model so the loaded baseline is tokenized the way consolidation expects. Resolve the effective model once and pass it to both:

```python
from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_user_memory.user_memory import load_user_memory
from unique_user_memory.user_memory_message_log import UserMemoryMessageLogger
from unique_user_memory.user_memory_postprocessor import UserMemoryPostprocessor

user_memory_config = config.agent.services.user_memory_config

# Resolve the effective model once and reuse it for load-time capping and
# consolidation so both use the same tokenizer.
memory_language_model = (
    config.space.language_model
    if user_memory_config.use_orchestrator_language_model
    else user_memory_config.language_model
)

message_step_logger = MessageStepLogger(chat_service)
memory_message_step_logger = UserMemoryMessageLogger(
    message_step_logger,
    logger=logger,
)
await memory_message_step_logger.log_loading_start()
user_memory_state = None
load_succeeded = False
try:
    user_memory_state = await load_user_memory(
        event=event,
        config=user_memory_config,
        language_model=memory_language_model,
        logger=logger,
    )
    load_succeeded = True
except Exception as exc:
    logger.warning(
        "[user-memory] load raised - running without memory: [%s] %s",
        type(exc).__name__,
        exc,
    )
finally:
    # Always close the RUNNING step — otherwise the chat Steps UI stays stuck
    # on "Loading context memory" for that turn when load raises.
    if not load_succeeded:
        await memory_message_step_logger.log_loading_failed()

if load_succeeded and user_memory_state is not None:
    await memory_message_step_logger.log_loading_complete(with_settings_entry=True)
    user_memory_text = user_memory_state.text
    postprocessor_manager.add_postprocessor(
        UserMemoryPostprocessor(
            config=user_memory_config,
            language_model=memory_language_model,
            event=event,
            state=user_memory_state,
            logger=logger,
            message_step_logger=memory_message_step_logger,
        )
    )
elif load_succeeded:
    await memory_message_step_logger.log_loading_complete(with_settings_entry=False)
```

Note that `UserMemoryPostprocessor` re-derives the effective model internally from `use_orchestrator_language_model`, so passing `memory_language_model` (rather than the raw orchestrator model) keeps its behavior identical while ensuring `load_user_memory` caps with the matching tokenizer.
