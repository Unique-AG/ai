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

## Human-readable responses (mandatory)

**Never show raw cron expressions to the user.** Always translate them into plain language. The cron syntax is only used in CLI commands — all communication with the user must describe the schedule in natural, human-readable terms.

| Cron expression | Say this to the user |
|-----------------|----------------------|
| `*/15 * * * *` | "every 15 minutes" |
| `0 9 * * 1-5` | "every weekday (Mon-Fri) at 9:00 AM" |
| `0 0 * * *` | "every day at midnight" |
| `0 8 1 * *` | "on the 1st of every month at 8:00 AM" |
| `30 17 * * 5` | "every Friday at 5:30 PM" |
| `0 */2 * * *` | "every 2 hours" |
| `0 9 * * 1` | "every Monday at 9:00 AM" |
| `0 9,17 * * 1-5` | "every weekday at 9:00 AM and 5:00 PM" |

**Rules:**
- When **confirming creation**, say e.g. "Done — scheduled to run **every weekday at 9:00 AM**." Never say "Created task with cron `0 9 * * 1-5`."
- When **listing tasks**, describe each schedule in words, e.g. "Daily report — runs **every weekday at 9:00 AM**, enabled."
- When the **user requests a schedule**, translate their words into the correct cron expression silently and pass it to the CLI. Confirm back in plain language.
- If the user says "every morning at 9" → use `0 9 * * *` but tell them "Scheduled to run **every day at 9:00 AM**."
- Include the day-of-week names (Mon, Tue, etc.) rather than numbers.
- Use 12-hour format with AM/PM for times when talking to the user.

## Timezone handling (critical)

**The platform runs all cron schedules in UTC.** The user almost certainly thinks in their local timezone. You **must** account for this difference or tasks will fire at the wrong time.

**Before creating or updating a schedule:**
1. Check if you already know the user's timezone (from prior conversation, system info, or profile).
2. If you do **not** know it, **ask**: "What timezone are you in? (e.g. Europe/Zurich, US/Eastern, Asia/Tokyo)"
3. Convert the user's desired local time to UTC before building the cron expression.
4. Confirm back in the **user's local timezone**, and mention the UTC equivalent.

**Conversion examples (Europe/Zurich, CET = UTC+1 / CEST = UTC+2):**

| User says (local) | Season | UTC offset | Cron (UTC) |
|--------------------|--------|------------|------------|
| "9:00 AM" | Winter (CET) | UTC+1 | `0 8 * * *` |
| "9:00 AM" | Summer (CEST) | UTC+2 | `0 7 * * *` |
| "5:30 PM" | Winter (CET) | UTC+1 | `30 16 * * *` |
| "midnight" | Winter (CET) | UTC+1 | `0 23 * * *` (previous day in UTC) |

**Rules:**
- Always tell the user the schedule in **their local time** first, then add "(UTC: HH:MM)" in parentheses.
- If the timezone has DST, warn the user: "Note: when daylight saving changes, the task will shift by one hour in your local time since the platform runs in UTC."
- For interval-based schedules like "every 15 minutes" or "every 2 hours", timezone conversion is not needed — just mention that these run around the clock in UTC.
- Store the user's timezone mentally for the rest of the conversation so you don't ask again.

**Example confirmation:**
> "Done — scheduled to run **every weekday at 9:00 AM (your time, Europe/Zurich)**. That's 7:00 AM UTC in summer / 8:00 AM UTC in winter. Note: the exact local time will shift by 1 hour when daylight saving changes."

## Agent workflow for creating a task

Before running `schedule create`, **ask the user**:

1. **Timezone** — If not already known, ask for it first. You need this to convert times correctly.
2. **Which assistant?** — The user must supply an assistant ID (starts with `assistant_`). If unknown, run `unique-cli schedule list` to show existing tasks or ask the user.
3. **New chat or existing chat?**
   - **New chat each run** (default) — omit `--chat-id`. Each execution creates a fresh chat.
   - **Continue an existing chat** — the user must provide a chat ID (starts with `chat_`). Pass it via `--chat-id`.
4. **When should it run?** — Ask in plain language (e.g. "every weekday at 9 AM"). Convert to a UTC cron expression.
5. **Prompt text** — what the assistant should do on each trigger.

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

### Translating user requests to cron

The user will describe schedules in plain language. Translate silently:

| User says | Cron expression |
|-----------|-----------------|
| "every 15 minutes" | `*/15 * * * *` |
| "every weekday at 9 AM" / "every morning Mon–Fri" | `0 9 * * 1-5` |
| "every day at midnight" | `0 0 * * *` |
| "first of every month at 8 AM" | `0 8 1 * *` |
| "every Friday at 5:30 PM" | `30 17 * * 5` |
| "every 2 hours" | `0 */2 * * *` |
| "twice a day at 9 AM and 5 PM, weekdays" | `0 9,17 * * 1-5` |
| "every Monday at 9 AM" | `0 9 * * 1` |
| "every hour" | `0 * * * *` |
| "every day at 6:30 AM" | `30 6 * * *` |

### Cron field reference (for the agent, not the user)

```
┌───────────── minute (0–59)
│ ┌───────────── hour (0–23)
│ │ ┌───────────── day of month (1–31)
│ │ │ ┌───────────── month (1–12)
│ │ │ │ ┌───────────── day of week (0–7, 0 and 7 = Sunday)
│ │ │ │ │
* * * * *
```

Day-of-week mapping: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun

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

User: "Schedule a daily sales report every weekday at 9 AM"

Agent (if timezone unknown): "What timezone are you in?"

User: "Zurich"

Agent thinks: Europe/Zurich, currently CEST (UTC+2), so 9:00 AM local = 7:00 AM UTC → cron `0 7 * * 1-5`

Run:
```bash
unique-cli schedule create \
  -c "0 7 * * 1-5" \
  -a assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  -p "Generate the daily sales report and email it to the team"
```

Respond: "Done — your daily sales report is scheduled to run **every weekday (Mon–Fri) at 9:00 AM your time (Europe/Zurich)**. That's 7:00 AM UTC. A new chat will be created for each run. Note: when clocks change for daylight saving, the task will shift by one hour in your local time."

### Set up a recurring task that continues the same chat

User: "I want to add daily numbers to an existing report chat at 9 AM"

Agent thinks: Already know timezone is Europe/Zurich (CEST), 9 AM local = 7 AM UTC

Run:
```bash
unique-cli schedule create \
  -c "0 7 * * 1-5" \
  -a assistant_cvj3fd7x8hpt1hfp0akqu1rq \
  --chat-id chat_b7ze6mpv0edy324yhjj1d92t \
  -p "Append today's numbers to the running report"
```

Respond: "Done — scheduled to run **every weekday (Mon–Fri) at 9:00 AM your time** (7:00 AM UTC), continuing chat `chat_b7ze6mpv0edy324yhjj1d92t`."

### Pause and resume a task

```bash
unique-cli schedule update <task_id> --disable
```
Respond: "The task has been **paused**. It won't run until you re-enable it."

```bash
unique-cli schedule update <task_id> --enable
```
Respond: "The task is **active** again and will run on its next scheduled time."

### Modify an existing task's schedule

User: "Change it to run every hour instead"

Agent thinks: "every hour" is interval-based, no timezone conversion needed.

Run:
```bash
unique-cli schedule update <task_id> --cron "0 * * * *"
```

Respond: "Updated — the task now runs **every hour**, on the hour (UTC). Since this is interval-based, it runs at the same wall-clock intervals regardless of timezone."

User: "Actually, make it run at 6:30 PM my time on Fridays"

Agent thinks: Europe/Zurich CEST (UTC+2), 6:30 PM = 16:30 UTC → cron `30 16 * * 5`

Run:
```bash
unique-cli schedule update <task_id> --cron "30 16 * * 5"
```

Respond: "Updated — the task now runs **every Friday at 6:30 PM your time** (4:30 PM UTC)."

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
