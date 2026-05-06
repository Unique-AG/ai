# ScheduledTask API

Create, list, retrieve, update, and delete cron-based scheduled tasks that trigger an assistant on a recurring schedule. Tasks are stored and executed on the Unique AI Platform via a Kubernetes CronJob — they are not local crontab entries.

## Overview

Each scheduled task defines:

- A **cron expression** (5-field, UTC) controlling when the task fires
- An **assistant** to execute on each trigger
- A **prompt** sent to the assistant
- An optional **chat ID** to continue an existing conversation (omit for a new chat each run)
- An **enabled** flag to pause/resume execution

The platform evaluates all enabled tasks every minute and triggers execution for those whose cron expression matches the current time.

!!! note "All times are UTC"
    Cron expressions are evaluated in UTC. Convert local times before creating or updating schedules.

## Methods

??? example "`unique_sdk.ScheduledTask.create` - Create a scheduled task"

    Create a new scheduled task.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `cronExpression` (str, required) - 5-field cron expression (e.g. `"0 9 * * 1-5"`)
    - `assistantId` (str, required) - ID of the assistant to execute (starts with `assistant_`)
    - `prompt` (str, required) - Prompt text sent to the assistant on each trigger
    - `chatId` (str, optional) - Chat ID to continue (starts with `chat_`). Omit for a new chat each run.
    - `enabled` (bool, optional) - Whether the task is active. Defaults to `True`.

    **Returns:**

    Returns a [`ScheduledTask`](#scheduledtask) object.

    **Example - New chat each run:**

    ```python
    task = unique_sdk.ScheduledTask.create(
        user_id="user_123",
        company_id="company_456",
        cronExpression="0 9 * * 1-5",
        assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
        prompt="Generate the daily sales report",
    )
    print(f"Created task: {task.id}")
    ```

    **Example - Continue an existing chat:**

    ```python
    task = unique_sdk.ScheduledTask.create(
        user_id="user_123",
        company_id="company_456",
        cronExpression="0 9 * * 1-5",
        assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
        chatId="chat_b7ze6mpv0edy324yhjj1d92t",
        prompt="Append today's numbers to the running report",
    )
    ```

    **Example - Create disabled:**

    ```python
    task = unique_sdk.ScheduledTask.create(
        user_id="user_123",
        company_id="company_456",
        cronExpression="*/15 * * * *",
        assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
        prompt="Check for new support tickets",
        enabled=False,
    )
    ```

??? example "`unique_sdk.ScheduledTask.list` - List all scheduled tasks"

    List all scheduled tasks for the authenticated user.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier

    **Returns:**

    Returns a list of [`ScheduledTask`](#scheduledtask) objects.

    **Example:**

    ```python
    tasks = unique_sdk.ScheduledTask.list(
        user_id="user_123",
        company_id="company_456",
    )
    for task in tasks:
        status = "enabled" if task.enabled else "disabled"
        print(f"{task.id}: {task.cronExpression} ({status})")
    ```

??? example "`unique_sdk.ScheduledTask.retrieve` - Get a scheduled task by ID"

    Retrieve full details of a single scheduled task.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `id` (str, required) - The scheduled task identifier

    **Returns:**

    Returns a [`ScheduledTask`](#scheduledtask) object.

    **Example:**

    ```python
    task = unique_sdk.ScheduledTask.retrieve(
        user_id="user_123",
        company_id="company_456",
        id="task_abc123",
    )
    print(f"Cron: {task.cronExpression}")
    print(f"Assistant: {task.assistantName} ({task.assistantId})")
    print(f"Prompt: {task.prompt}")
    print(f"Enabled: {task.enabled}")
    ```

??? example "`unique_sdk.ScheduledTask.modify` - Update a scheduled task"

    Update an existing scheduled task. Only the fields you provide are changed; everything else stays the same.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `id` (str, required) - The scheduled task identifier
    - `cronExpression` (str, optional) - Updated cron expression
    - `assistantId` (str, optional) - Updated assistant ID
    - `prompt` (str, optional) - Updated prompt text
    - `chatId` (str | None, optional) - Updated chat ID. Pass `None` to clear (new chat each run).
    - `enabled` (bool, optional) - Enable or disable the task

    **Returns:**

    Returns the updated [`ScheduledTask`](#scheduledtask) object.

    **Example - Disable a task:**

    ```python
    task = unique_sdk.ScheduledTask.modify(
        user_id="user_123",
        company_id="company_456",
        id="task_abc123",
        enabled=False,
    )
    ```

    **Example - Change schedule and prompt:**

    ```python
    task = unique_sdk.ScheduledTask.modify(
        user_id="user_123",
        company_id="company_456",
        id="task_abc123",
        cronExpression="0 */2 * * *",
        prompt="Check inbox every 2 hours",
    )
    ```

    **Example - Clear chat ID (new chat each run):**

    ```python
    task = unique_sdk.ScheduledTask.modify(
        user_id="user_123",
        company_id="company_456",
        id="task_abc123",
        chatId=None,
    )
    ```

??? example "`unique_sdk.ScheduledTask.delete` - Delete a scheduled task"

    Permanently delete a scheduled task. This action cannot be undone.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `id` (str, required) - The scheduled task identifier

    **Returns:**

    Returns a `DeletedObject` dict with `id`, `object`, and `deleted` fields.

    **Example:**

    ```python
    result = unique_sdk.ScheduledTask.delete(
        user_id="user_123",
        company_id="company_456",
        id="task_abc123",
    )
    if result["deleted"]:
        print(f"Deleted task {result['id']}")
    ```

## Async Methods

All methods have async variants with an `_async` suffix:

- `create_async`
- `list_async`
- `retrieve_async`
- `modify_async`
- `delete_async`

```python
task = await unique_sdk.ScheduledTask.create_async(
    user_id="user_123",
    company_id="company_456",
    cronExpression="0 9 * * 1-5",
    assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
    prompt="Generate daily report",
)
```

## Return Types

#### ScheduledTask {#scheduledtask}

??? note "The `ScheduledTask` object represents a cron-based scheduled task"

    **Fields:**

    - `id` (str) - Unique task identifier
    - `object` (str) - Object type (`"scheduled_task"`)
    - `cronExpression` (str) - 5-field cron expression (UTC)
    - `assistantId` (str) - ID of the assistant to execute
    - `assistantName` (str | None) - Display name of the assistant
    - `chatId` (str | None) - Chat ID to continue, or `None` for new chat each run
    - `prompt` (str) - Prompt text sent on each trigger
    - `enabled` (bool) - Whether the task is active
    - `lastRunAt` (str | None) - ISO 8601 timestamp of the last execution, or `None`
    - `createdAt` (str) - ISO 8601 creation timestamp
    - `updatedAt` (str) - ISO 8601 last update timestamp

    **Returned by:** `create()`, `list()`, `retrieve()`, `modify()`

## Cron Expression Reference

Cron expressions use 5 fields (UTC):

```
┌───────────── minute (0–59)
│ ┌───────────── hour (0–23)
│ │ ┌───────────── day of month (1–31)
│ │ │ ┌───────────── month (1–12)
│ │ │ │ ┌───────────── day of week (0–7, 0 and 7 = Sunday)
│ │ │ │ │
* * * * *
```

| Expression | Schedule |
|------------|----------|
| `*/15 * * * *` | Every 15 minutes |
| `0 9 * * 1-5` | Weekdays at 09:00 UTC |
| `0 0 * * *` | Daily at midnight UTC |
| `0 8 1 * *` | 1st of every month at 08:00 UTC |
| `30 17 * * 5` | Every Friday at 17:30 UTC |

## Related Resources

- [CLI Scheduled Tasks](../cli/scheduled_tasks.md) - Manage scheduled tasks from the command line
- [Message API](message.md) - Manage chat messages
