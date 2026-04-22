# Scheduled Tasks - Examples (experimental)

!!! warning "Experimental"
    `ScheduledTasks` lives under `unique_toolkit.experimental.scheduled_task`.
    The public API, method names, and argument shapes may change without
    notice and are **not** covered by the toolkit's normal stability
    guarantees. Pin the toolkit version if you depend on a specific shape.

A scheduled task is a cron-triggered assistant run: on every fire the server
executes a configured assistant with a preset prompt, optionally continuing a
specific chat. The `ScheduledTasks` service wraps
[`unique_sdk.ScheduledTask`](../../../api.md) so you can create, list, update
and delete those triggers from Python with sync and async variants.

For the broader experimental surface see
[`unique_toolkit.experimental`](../../../api.md).

<!--
```{.python #scheduled_tasks_imports}
from unique_toolkit.experimental.scheduled_task import (
    Cron,
    ScheduledTasks,
)
```
-->

## Instantiating the service

`ScheduledTasks` follows the same constructor pattern as the other toolkit
services:

- `ScheduledTasks.from_settings(settings)` - accepts a `UniqueSettings`
  instance. Load the settings explicitly (e.g. `UniqueSettings.from_env()` in
  standalone scripts and notebooks) and pass them in — the service never
  reads environment variables on its own.
- `ScheduledTasks.from_context(context)` - binds to an existing
  `UniqueContext` (typical inside event-driven handlers).
- `ScheduledTasks(user_id=..., company_id=...)` - lowest-level form when you
  already have the two identifiers.

```{.python #scheduled_tasks_setup_from_settings}
settings = UniqueSettings.from_env()
scheduled_tasks = ScheduledTasks.from_settings(settings)
```

<!--
```{.python #scheduled_tasks_setup file=./docs/.python_files/scheduled_tasks_setup.py}
<<common_imports>>
<<scheduled_tasks_imports>>
<<scheduled_tasks_setup_from_settings>>
```
-->

## The Cron catalogue

The server expects a classic 5-field UTC cron expression
(`"minute hour day-of-month month day-of-week"`). To save you from typing
these by hand, the subpackage ships a `Cron` `StrEnum` of the most common
schedules. Every member **is** a string, so you can drop it straight into
`create` without any conversion:

```{.python #scheduled_tasks_cron_examples}
Cron.DAILY_MIDNIGHT         # "0 0 * * *"
Cron.WEEKDAYS_9AM           # "0 9 * * 1-5"
Cron.EVERY_FIFTEEN_MINUTES  # "*/15 * * * *"
Cron.HOURLY                 # "0 * * * *"
```

For schedules that are not in the catalogue, pass a raw cron string - the
service forwards it verbatim to the server.

## Create a scheduled task

Register a new trigger with a cron expression, an assistant id and the prompt
the assistant receives on every fire. The server creates a fresh chat on every
trigger unless you pin one with `chat_id=`.

```{.python #scheduled_tasks_create}
task = scheduled_tasks.create(
    cron_expression=Cron.WEEKDAYS_9AM,
    assistant_id="assistant_daily_report",
    prompt="Summarise yesterday's key events and email me the briefing.",
)

print(task.id, task.cron_expression, task.enabled)
```

Pass `enabled=False` to register the task in a paused state, or `chat_id=` to
continue an existing chat rather than starting a new one on every run.

<!--
```{.python file=./docs/.python_files/scheduled_tasks_create_task.py}
<<common_imports>>
<<scheduled_tasks_imports>>
<<scheduled_tasks_setup_from_settings>>
<<scheduled_tasks_create>>
```
-->

## List and get tasks

`list()` returns every scheduled task visible to the acting user as fully
parsed `ScheduledTask` models. Use `get(task_id=...)` to fetch a single
one:

```{.python #scheduled_tasks_list_and_get}
for task in scheduled_tasks.list():
    print(task.id, task.cron_expression, task.prompt[:40])

detail = scheduled_tasks.get(task_id=task.id)
```

<!--
```{.python file=./docs/.python_files/scheduled_tasks_list_tasks.py}
<<common_imports>>
<<scheduled_tasks_imports>>
<<scheduled_tasks_setup_from_settings>>
<<scheduled_tasks_list_and_get>>
```
-->

## Update an existing task

`update` performs a server-side partial update: only the keyword arguments
you pass are sent, every other field keeps its current value. The most common
adjustments are changing the schedule, swapping the assistant, or flipping
`enabled` on and off:

```{.python #scheduled_tasks_update_schedule_and_enable}
updated = scheduled_tasks.update(
    task_id=task.id,
    cron_expression=Cron.EVERY_FIFTEEN_MINUTES,
    enabled=True,
)
```

### Clearing the chat link

`chat_id` has two mutually-exclusive intents, so the signature splits them
explicitly:

- `chat_id="chat_..."` - repoint the task at a specific chat.
- `clear_chat_id=True` - drop the current chat link so the server spawns a
  fresh chat on every trigger.

Omit both to leave the chat setting untouched. Combining them raises
`TypeError` locally, before any SDK call:

```{.python #scheduled_tasks_clear_chat_id}
scheduled_tasks.update(
    task_id=task.id,
    clear_chat_id=True,
)
```

<!--
```{.python file=./docs/.python_files/scheduled_tasks_update_task.py}
<<common_imports>>
<<scheduled_tasks_imports>>
<<scheduled_tasks_setup_from_settings>>
<<scheduled_tasks_create>>
<<scheduled_tasks_update_schedule_and_enable>>
<<scheduled_tasks_clear_chat_id>>
```
-->

## Delete a task

Deletion is permanent and cannot be undone. The method returns a
`DeletedScheduledTask` acknowledgement echoed from the server:

```{.python #scheduled_tasks_delete}
ack = scheduled_tasks.delete(task_id=task.id)
assert ack.deleted is True
```

<!--
```{.python file=./docs/.python_files/scheduled_tasks_delete_task.py}
<<common_imports>>
<<scheduled_tasks_imports>>
<<scheduled_tasks_setup_from_settings>>
<<scheduled_tasks_create>>
<<scheduled_tasks_delete>>
```
-->

## Async variants

Every public method has an `_async` counterpart with the same signature, for
use inside `async def` handlers:

```{.python #scheduled_tasks_async}
task = await scheduled_tasks.create_async(
    cron_expression=Cron.HOURLY,
    assistant_id="assistant_hourly_digest",
    prompt="Write a one-paragraph digest of the past hour.",
)

tasks = await scheduled_tasks.list_async()
await scheduled_tasks.delete_async(task_id=task.id)
```

<!--
```{.python file=./docs/.python_files/scheduled_tasks_async.py}
import asyncio

<<common_imports>>
<<scheduled_tasks_imports>>
<<scheduled_tasks_setup_from_settings>>


async def main() -> None:
    <<scheduled_tasks_async>>


asyncio.run(main())
```
-->

## Full examples

??? example "Full Examples (Click to expand)"

    <!--codeinclude-->
    [Create a task](../../../examples_from_docs/scheduled_tasks_create_task.py)
    [List tasks](../../../examples_from_docs/scheduled_tasks_list_tasks.py)
    [Update a task](../../../examples_from_docs/scheduled_tasks_update_task.py)
    [Delete a task](../../../examples_from_docs/scheduled_tasks_delete_task.py)
    [Async variants](../../../examples_from_docs/scheduled_tasks_async.py)
    <!--/codeinclude-->
