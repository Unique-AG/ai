# Scheduled Tasks

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

Manage cron-based scheduled tasks that trigger an assistant on a recurring schedule. Tasks are stored and executed on the Unique AI Platform (via a Kubernetes CronJob), not locally.

## schedule list

List all scheduled tasks for the authenticated user.

**One-shot:**

```bash
unique-cli schedule list
```

**Interactive shell:**

```
/> schedule list
1 scheduled task(s):

STATUS  CRON           ASSISTANT     PROMPT               ID          LAST RUN
on      0 9 * * 1-5    Report Bot    Generate the daily…  task_abc    2026-04-01 09:00
```

---

## schedule get

Get full details of a single scheduled task.

**Synopsis:**

```
schedule get <task_id>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `task_id` | The scheduled task identifier |

**Example:**

```bash
unique-cli schedule get task_abc123
```

```
ID:         task_abc123
Cron:       0 9 * * 1-5
Assistant:  Report Bot (assistant_cvj3fd7x8hpt1hfp0akqu1rq)
Chat ID:    (new chat each run)
Prompt:     Generate the daily sales report
Enabled:    yes
Last run:   2026-04-01 09:00
Created:    2026-04-01 08:00
Updated:    2026-04-01 09:00
```

---

## schedule create

Create a new scheduled task.

**Synopsis:**

```
schedule create --cron <expr> --assistant <id> --prompt <text> [--chat-id <id>] [--disabled]
```

**Options:**

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--cron` | `-c` | Yes | 5-field cron expression (UTC) |
| `--assistant` | `-a` | Yes | Assistant ID to execute (starts with `assistant_`) |
| `--prompt` | `-p` | Yes | Prompt text sent each run |
| `--chat-id` | | No | Continue an existing chat (starts with `chat_`). Omit for a new chat each run. |
| `--disabled` | | No | Create in a disabled state |

**Examples:**

```bash
# Create a weekday report task
unique-cli schedule create \
  --cron "0 9 * * 1-5" \
  --assistant assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  --prompt "Generate the daily sales report"

# Continue an existing chat
unique-cli schedule create \
  -c "0 9 * * 1-5" \
  -a assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  --chat-id chat_b7ze6mpv0edy324yhjj1d92t \
  -p "Append today's numbers to the running report"

# Create disabled
unique-cli schedule create \
  -c "*/15 * * * *" -a assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  -p "Check for new tickets" --disabled
```

**Interactive shell:**

```
/> schedule create -c "0 9 * * 1-5" -a assistant_cvj3fd7x8hpt1hfp0akqu1rq -p "Daily report"
Created scheduled task task_abc123

ID:         task_abc123
Cron:       0 9 * * 1-5
...
```

---

## schedule update

Update an existing scheduled task. Only the fields you provide are changed.

**Synopsis:**

```
schedule update <task_id> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `task_id` | The scheduled task identifier |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--cron` | `-c` | Updated cron expression |
| `--assistant` | `-a` | Updated assistant ID (starts with `assistant_`) |
| `--prompt` | `-p` | Updated prompt text |
| `--chat-id` | | Updated chat ID (starts with `chat_`). Use `none` to clear. |
| `--enable` | | Enable the task |
| `--disable` | | Disable the task |

!!! note
    `--enable` and `--disable` cannot be used together.

**Examples:**

```bash
# Change the schedule
unique-cli schedule update task_abc123 --cron "0 */2 * * *"

# Disable a task
unique-cli schedule update task_abc123 --disable

# Enable and change the prompt
unique-cli schedule update task_abc123 --enable --prompt "Updated daily report"

# Clear the chat ID (switch to new chat each run)
unique-cli schedule update task_abc123 --chat-id none
```

---

## schedule delete

Permanently delete a scheduled task. This action cannot be undone.

**Synopsis:**

```
schedule delete <task_id>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `task_id` | The scheduled task identifier |

**Example:**

```bash
unique-cli schedule delete task_abc123
Deleted scheduled task task_abc123
```

---

## Cron Expression Reference

Cron expressions use 5 fields and are evaluated in **UTC**:

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
| `0 */2 * * *` | Every 2 hours |

!!! tip "Timezone"
    All cron expressions are in UTC. Convert your local time before creating schedules. For example, 9:00 AM Central European Summer Time (CEST, UTC+2) is `0 7 * * *` in UTC.

## Related

- [ScheduledTask API Reference](../api_resources/scheduled_task.md) - Python SDK methods
- [Command Reference](commands.md) - All CLI commands
