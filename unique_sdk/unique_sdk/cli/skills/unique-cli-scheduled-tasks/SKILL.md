---
name: unique-cli-scheduled-tasks
description: >-
  Manage cron-based scheduled tasks on the Unique AI Platform using the
  unique-cli schedule command. Use when the user asks to schedule,
  automate, or set up recurring assistant executions, or when they need
  to list, create, update, enable, disable, or delete scheduled tasks.
  Each task defines a cron expression, an assistant, and a prompt that
  triggers on the defined schedule.
---

# Unique CLI -- Scheduled Tasks

Manage cron-tab style scheduled tasks that trigger an assistant on a recurring schedule. A Kubernetes CronJob evaluates all enabled tasks every minute and triggers assistant execution for those whose cron expression matches the current time.

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

```bash
unique-cli schedule create \
  --cron "0 9 * * 1-5" \
  --assistant clx1abc2d0001abcdef123456 \
  --prompt "Generate the daily sales report and email it to the team"
```

### Create options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--cron` | `-c` | Yes | 5-field cron expression |
| `--assistant` | `-a` | Yes | Assistant ID to execute |
| `--prompt` | `-p` | Yes | Prompt text sent each run |
| `--chat-id` | | No | Continue an existing chat (omit for new chat each run) |
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
│ ││ │ │
* * * * *
```

## Update a Scheduled Task

Only the fields you provide are changed; everything else stays the same.

```bash
# Change the schedule
unique-cli schedule update clx3ghi4f --cron "0 9 * * 1-5"

# Disable a task
unique-cli schedule update clx3ghi4f --disable

# Enable and change prompt
unique-cli schedule update clx3ghi4f --enable --prompt "Updated daily report"

# Clear the chat ID (new chat each run)
unique-cli schedule update clx3ghi4f --chat-id none
```

### Update options

| Option | Short | Description |
|--------|-------|-------------|
| `--cron` | `-c` | Updated cron expression |
| `--assistant` | `-a` | Updated assistant ID |
| `--prompt` | `-p` | Updated prompt text |
| `--chat-id` | | Updated chat ID (`none` to clear) |
| `--enable` | | Enable the task |
| `--disable` | | Disable the task |

## Delete a Scheduled Task

```bash
unique-cli schedule delete clx3ghi4f0003mnopqr345678
```

This action cannot be undone.

## Workflow Examples

### Set up a daily report

```bash
# Create a weekday 9 AM report task
unique-cli schedule create \
  -c "0 9 * * 1-5" \
  -a clx1abc2d0001abcdef123456 \
  -p "Generate the daily sales report and email it to the team"

# Verify it was created
unique-cli schedule list
```

### Pause and resume a task

```bash
# Disable temporarily
unique-cli schedule update clx3ghi4f --disable

# Re-enable later
unique-cli schedule update clx3ghi4f --enable
```

### Modify an existing task's schedule

```bash
# Switch from every 15 min to once an hour
unique-cli schedule update clx3ghi4f --cron "0 * * * *"
```

## SDK Usage (Python)

The CLI is backed by the `unique_sdk.ScheduledTask` API resource:

```python
import unique_sdk

unique_sdk.api_key = "ukey_..."
unique_sdk.app_id = "app_..."

# Create
task = unique_sdk.ScheduledTask.create(
    user_id="user_123",
    company_id="company_456",
    cronExpression="0 9 * * 1-5",
    assistantId="clx1abc2d0001abcdef123456",
    prompt="Generate daily report",
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
    id="clx3ghi4f0003mnopqr345678",
)

# Update
task = unique_sdk.ScheduledTask.modify(
    user_id="user_123",
    company_id="company_456",
    id="clx3ghi4f0003mnopqr345678",
    enabled=False,
)

# Delete
unique_sdk.ScheduledTask.delete(
    user_id="user_123",
    company_id="company_456",
    id="clx3ghi4f0003mnopqr345678",
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
