---
name: unique-cli-scheduled-tasks
description: >-
  ALWAYS use this skill when the user asks to schedule, automate, set up
  recurring tasks, create a cron job, or anything involving timed /
  periodic execution.  Do NOT use the local system crontab — scheduled
  tasks are stored on the Unique AI Platform and executed by a
  Kubernetes CronJob, not locally.  This skill covers creating,
  listing, updating, enabling, disabling, and deleting scheduled tasks
  via the unique-cli schedule command.
---

# Unique CLI -- Scheduled Tasks

Manage cron-tab style scheduled tasks that trigger an assistant on a recurring schedule. Tasks are **stored and executed on the Unique AI Platform** (via a Kubernetes CronJob that evaluates all enabled tasks every minute). They are **not** local crontab entries — do not fall back to `crontab -e` or similar OS-level scheduling.

> **Important — always use this skill** whenever the user mentions scheduling, recurring execution, cron jobs, timed tasks, or automation. Even if the phrasing sounds like a local cron job, the correct approach is `unique-cli schedule`.

## Agent workflow for creating a task

Before running `schedule create`, **ask the user**:

1. **Which assistant?** — The user must supply an assistant ID (starts with `assistant_`). If unknown, run `unique-cli schedule list` to show existing tasks or ask the user.
2. **New chat or existing chat?**
   - **New chat each run** (default) — omit `--chat-id`. Each execution creates a fresh chat.
   - **Continue an existing chat** — the user must provide a chat ID (starts with `chat_`). Pass it via `--chat-id`.
3. **Cron expression** — help the user pick the right schedule (see reference below).
4. **Prompt text** — what the assistant should do on each trigger.

Only pass `--chat-id` when the user explicitly wants to continue a specific chat. Otherwise leave it out.

## ID formats

| Entity | Prefix | Example |
|--------|--------|---------|
| Assistant | `assistant_` | `assistant_cvj3fd7x8hpt1hfp0akqu1rq` |
| Chat | `chat_` | `chat_b7ze6mpv0edy324yhjj1d92t` |

## List Scheduled Tasks

```bash
unique-cli schedule list
```

Output shows a table with status, cron expression, assistant, prompt snippet, task ID, and last run time.

## Get Task Details

```bash
unique-cli schedule get <task_id>
```

Shows full details of a single task including all fields.

## Create a Scheduled Task

### New chat each run (default — no `--chat-id`)

```bash
unique-cli schedule create \
  --cron "0 9 * * 1-5" \
  --assistant assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  --prompt "Generate the daily sales report and email it to the team"
```

### Continue an existing chat

```bash
unique-cli schedule create \
  --cron "0 9 * * 1-5" \
  --assistant assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  --chat-id chat_b7ze6mpv0edy324yhjj1d92t \
  --prompt "Append today's numbers to the running report"
```

### Create options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--cron` | `-c` | Yes | 5-field cron expression |
| `--assistant` | `-a` | Yes | Assistant ID to execute (starts with `assistant_`) |
| `--prompt` | `-p` | Yes | Prompt text sent each run |
| `--chat-id` | | No | Continue an existing chat (starts with `chat_`; **omit for new chat each run**) |
| `--disabled` | | No | Create in disabled state |

### Common cron expressions

| Expression | Meaning |
|------------|---------|
| `*/15 * * * *` | Every 15 minutes |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `0 0 * * *` | Daily at midnight |
| `0 8 1 * *` | First day of every month at 8:00 AM |
| `30 17 * * 5` | Every Friday at 5:30 PM |

### Cron field reference

```
┌───────────── minute (0–59)
│ ┌───────────── hour (0–23)
│ │ ┌───────────── day of month (1–31)
│ │ │ ┌───────────── month (1–12)
│ │ │ │ ┌───────────── day of week (0–7, 0 and 7 = Sunday)
│ │ │ │ │
* * * * *
```

## Update a Scheduled Task

Only the fields you provide are changed; everything else stays the same.

```bash
# Change the schedule
unique-cli schedule update <task_id> --cron "0 9 * * 1-5"

# Disable a task
unique-cli schedule update <task_id> --disable

# Enable and change prompt
unique-cli schedule update <task_id> --enable --prompt "Updated daily report"

# Clear the chat ID (new chat each run)
unique-cli schedule update <task_id> --chat-id none
```

### Update options

| Option | Short | Description |
|--------|-------|-------------|
| `--cron` | `-c` | Updated cron expression |
| `--assistant` | `-a` | Updated assistant ID (starts with `assistant_`) |
| `--prompt` | `-p` | Updated prompt text |
| `--chat-id` | | Updated chat ID (starts with `chat_`; `none` to clear) |
| `--enable` | | Enable the task |
| `--disable` | | Disable the task |

## Delete a Scheduled Task

```bash
unique-cli schedule delete <task_id>
```

This action cannot be undone.

## Workflow Examples

### Set up a daily report (new chat each run)

```bash
unique-cli schedule create \
  -c "0 9 * * 1-5" \
  -a assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  -p "Generate the daily sales report and email it to the team"

unique-cli schedule list
```

### Set up a recurring task that continues the same chat

```bash
unique-cli schedule create \
  -c "0 9 * * 1-5" \
  -a assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  --chat-id chat_b7ze6mpv0edy324yhjj1d92t \
  -p "Append today's numbers to the running report"
```

### Pause and resume a task

```bash
unique-cli schedule update <task_id> --disable
unique-cli schedule update <task_id> --enable
```

### Modify an existing task's schedule

```bash
unique-cli schedule update <task_id> --cron "0 * * * *"
```

## SDK Usage (Python)

The CLI is backed by the `unique_sdk.ScheduledTask` API resource:

```python
import unique_sdk

unique_sdk.api_key = "ukey_..."
unique_sdk.app_id = "app_..."

# Create (new chat each run — no chatId)
task = unique_sdk.ScheduledTask.create(
    user_id="user_123",
    company_id="company_456",
    cronExpression="0 9 * * 1-5",
    assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
    prompt="Generate daily report",
)

# Create (continue existing chat)
task = unique_sdk.ScheduledTask.create(
    user_id="user_123",
    company_id="company_456",
    cronExpression="0 9 * * 1-5",
    assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
    chatId="chat_b7ze6mpv0edy324yhjj1d92t",
    prompt="Append today's data",
)

# List
tasks = unique_sdk.ScheduledTask.list(
    user_id="user_123",
    company_id="company_456",
)

# Retrieve
task = unique_sdk.ScheduledTask.retrieve(
    user_id="user_123",
    company_id="company_456",
    id="<task_id>",
)

# Update
task = unique_sdk.ScheduledTask.modify(
    user_id="user_123",
    company_id="company_456",
    id="<task_id>",
    enabled=False,
)

# Delete
unique_sdk.ScheduledTask.delete(
    user_id="user_123",
    company_id="company_456",
    id="<task_id>",
)
```

All methods have `*_async` variants for async usage.

## Prerequisites

Requires these environment variables:

```bash
UNIQUE_API_KEY    # API key (ukey_...)
UNIQUE_APP_ID     # App ID (app_...)
UNIQUE_USER_ID    # User ID
UNIQUE_COMPANY_ID # Company ID
```

Install: `pip install unique-sdk`
