---
name: unique-cli-scheduled-tasks
description: >-
  ALWAYS use this skill when the user asks to schedule, automate, set up
  recurring tasks, create a cron job, or anything involving timed /
  periodic execution.  Do NOT use the local system crontab — scheduled
  tasks are stored on the Unique AI Platform and executed by a
  Kubernetes CronJob, not locally.  Scheduled tasks always run on the
  current assistant (`$UNIQUE_ASSISTANT_ID`); never ask the user which
  assistant to use, neither in chat nor via `unique-cli elicit ask`.
  This skill covers creating, listing, updating, enabling, disabling,
  and deleting scheduled tasks via the unique-cli schedule command.
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
| `0 8 L * *` | "on the last day of every month at 8:00 AM" |
| `0 8 30 * *` | "on the 30th of every month at 8:00 AM — on the last day in February" |
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
- Always tell the user the **name** you gave the task when you create or rename it, e.g.
  "Done — I created **Daily sales report**, running every weekday at 9:00 AM."

## Monthly schedules and the last day of the month (critical)

**Write monthly schedules only as `minute hour day * *`**, where `day` is `1`–`30` or the `L`
token. In that form — and *only* in that form — a day the month does not have moves to the
month's last day instead of being skipped. A day list (`0 8 29,30,31 * *`), a range, a step or
a month restriction (`0 8 31 1,7 *`) falls outside that handling and **will** skip short
months, after you have told the user it would not.

**Rules:**
- **Never tell the user a month will be skipped.** In the supported form it is not — the run
  moves to that month's last day.
- For **"the last day of every month"**, and for **"the 31st"**, use the `L` token:
  `0 8 L * *`. `L` means the last day of whichever month it is, so it runs in all 12 months:
  31 January, 28 (or 29) February, 31 March, 30 April, and so on. Prefer `L` over `31` — it
  says what it means and is unambiguous in every month.
- When the user asks for **the 29th or 30th**, keep that day (`0 8 30 * *`) and spell out
  February: "…on the **30th of every month** — in February it runs on the **last day** of the
  month."
- Never put `L` anywhere but the day-of-month field, and never combine it with a list, range
  or step.
- The platform supports **daily, weekday, weekly and monthly** schedules. If the user asks for
  something outside that — a yearly date such as a birthday, "every two weeks", or a one-off
  reminder — say so plainly and offer the closest supported schedule. Do **not** invent a cron
  expression that pins the month (`0 7 18 11 *`) to fake it: it will run, but the schedule
  editor cannot display or edit it afterwards.

## Timezone handling (critical)

**Write the cron in the user's local wall-clock time and always pass `--timezone`.** The
platform evaluates the cron in that IANA timezone and keeps the local run time across daylight
saving changes. Never convert local times to UTC. Never mention UTC equivalents or daylight
saving shifts to the user.

The CLI **rejects** `schedule create` without `--timezone`, and rejects `schedule update` that
changes `--cron` without `--timezone`.

**Where the timezone comes from, in order:**
1. The `User's timezone` line in the system prompt (browser-detected IANA name).
2. A timezone already established earlier in the conversation.
3. Otherwise, **ask**: "What timezone are you in? (e.g. Europe/Zurich, America/New_York, Asia/Tokyo)"

**Rules:**
- Use **IANA names only** (`Europe/Zurich`, `America/New_York`, `Asia/Tokyo`). Never use
  abbreviations (`CET`, `EST`) or UTC offsets (`+02:00`, `UTC+2`). The platform rejects them.
- Pass `--timezone <IANA>` on every `create`, and on every `update` that changes `--cron`.
- Write the cron for the user's local time. "9:00 AM in Zurich" → `-c "0 9 * * *"` `-tz Europe/Zurich`.
- Confirm back in the user's local time only. Do **not** add "(UTC: …)" or warn about DST.
- For interval schedules like "every 15 minutes", still pass `--timezone`.
- Store the user's timezone for the rest of the conversation so you don't ask again.
- To schedule explicitly in UTC, pass `--timezone UTC`.

**Legacy tasks without a timezone:** If `schedule get` shows `Timezone: UTC` on a task the user
thinks of in local time, any update to its schedule **must** pass the new local cron and
`--timezone` together. Changing only the timezone reinterprets the old UTC cron as local time.

**Example confirmation:**
> "Done — scheduled to run **every weekday at 9:00 AM your time (Europe/Zurich)**."

## Agent workflow for creating a task

!!! danger "Never ask the user which assistant to schedule"
    The scheduled task **must always run on the current assistant** — the same
    assistant the user is talking to right now. **Never** prompt the user for
    an assistant ID, neither in chat nor via `unique-cli elicit ask`. Read the
    `UNIQUE_ASSISTANT_ID` environment variable and pass it as `--assistant`
    verbatim. If `UNIQUE_ASSISTANT_ID` is unset, stop and tell the user the
    environment is missing — do **not** fall back to asking them.

Before running `schedule create`, **resolve / ask the user**:

1. **Assistant** — Use `$UNIQUE_ASSISTANT_ID` (the current assistant). Do not
   ask. Do not run `unique-cli schedule list` to "find" one. Do not start an
   elicitation. If the env var is missing, surface that as an error and stop.
2. **Timezone** — Prefer the `User's timezone` line in the system prompt. If
   missing and not already known, ask. You need an IANA name for `--timezone`.
3. **New chat or existing chat?**
   - **New chat each run** (default) — omit `--chat-id`. Each execution creates a fresh chat.
   - **Continue an existing chat** — the user must provide a chat ID (starts with `chat_`). Pass it via `--chat-id`.
4. **When should it run?** — Ask in plain language (e.g. "every weekday at 9 AM"). Translate to a **local-time** cron expression; do not convert to UTC.
5. **Prompt text** — what the assistant should do on each trigger.
6. **Name** — **you write it, do not ask for it.** Derive a short, descriptive label from the
   prompt (a few words, title-style, e.g. "Daily sales report", "Weekly pipeline review").
   Pass it as `--name`. Keep it **at most 128 characters** — a longer name is rejected and the
   whole `schedule create` fails. Tell the user what you called it when you confirm.

Only pass `--chat-id` when the user explicitly wants to continue a specific chat. Otherwise leave it out.

!!! tip "Confirming the assistant in plain language"
    When you confirm the schedule back to the user, just say "this assistant"
    (or its display name if you already know it from the chat context). Do
    **not** read the raw `assistant_…` ID back to the user.

## ID formats

| Entity | Prefix | Example |
|--------|--------|---------|
| Assistant | `assistant_` | `assistant_cvj3fd7x8hpt1hfp0akqu1rq` |
| Chat | `chat_` | `chat_b7ze6mpv0edy324yhjj1d92t` |

## List Scheduled Tasks

```bash
unique-cli schedule list
```

Output shows a table with status, name, cron expression, timezone, assistant, prompt snippet, task ID, and last run time. A task saved without a name shows its prompt snippet in the name column.

## Get Task Details

```bash
unique-cli schedule get <task_id>
```

Shows full details of a single task including all fields.

## Create a Scheduled Task

Always pass `--assistant "$UNIQUE_ASSISTANT_ID"` so the task runs on the
current assistant. Do not substitute a literal `assistant_…` ID and do not
ask the user to provide one. Always pass `--timezone` with an IANA name.

### New chat each run (default — no `--chat-id`)

```bash
unique-cli schedule create \
  --cron "0 9 * * 1-5" \
  --timezone Europe/Zurich \
  --assistant "$UNIQUE_ASSISTANT_ID" \
  --prompt "Generate the daily sales report and email it to the team" \
  --name "Daily sales report"
```

### Continue an existing chat

```bash
unique-cli schedule create \
  --cron "0 9 * * 1-5" \
  --timezone Europe/Zurich \
  --assistant "$UNIQUE_ASSISTANT_ID" \
  --chat-id chat_b7ze6mpv0edy324yhjj1d92t \
  --prompt "Append today's numbers to the running report" \
  --name "Running report top-up"
```

### Create options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--cron` | `-c` | Yes | 5-field cron expression in the user's local time |
| `--timezone` | `-tz` | Yes | IANA timezone the cron runs in (e.g. `Europe/Zurich`). Use `UTC` for UTC. |
| `--assistant` | `-a` | Yes | Assistant ID to execute (starts with `assistant_`). **Always pass `"$UNIQUE_ASSISTANT_ID"`** — never ask the user. |
| `--prompt` | `-p` | Yes | Prompt text sent each run |
| `--name` | `-n` | No | Short label shown in the UI (≤128 chars). **Always pass one** — you generate it; without it the UI falls back to the prompt text |
| `--chat-id` | | No | Continue an existing chat (starts with `chat_`; **omit for new chat each run**) |
| `--disabled` | | No | Create in disabled state |

### Translating user requests to cron

The user will describe schedules in plain language. Translate silently into **local-time** cron:

| User says | Cron expression |
|-----------|-----------------|
| "every 15 minutes" | `*/15 * * * *` |
| "every weekday at 9 AM" / "every morning Mon–Fri" | `0 9 * * 1-5` |
| "every day at midnight" | `0 0 * * *` |
| "first of every month at 8 AM" | `0 8 1 * *` |
| "the 31st of every month at 8 AM" | `0 8 L * *` (the 31st means the last day) |
| "the 30th of every month at 8 AM" | `0 8 30 * *` (February runs on its last day) |
| "last day of every month at 8 AM" | `0 8 L * *` |
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
│ │ ┌───────────── day of month (1–31, or L for the last day)
│ │ │ ┌───────────── month (1–12)
│ │ │ │ ┌───────────── day of week (0–7, 0 and 7 = Sunday)
│ │ │ │ │
* * * * *
```

Day-of-week mapping: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun

## Update a Scheduled Task

Only the fields you provide are changed; everything else stays the same.
When changing `--cron`, you **must** also pass `--timezone`.

```bash
# Change the schedule (timezone required with --cron)
unique-cli schedule update <task_id> --cron "0 9 * * 1-5" --timezone Europe/Zurich

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
| `--cron` | `-c` | Updated cron expression (requires `--timezone`) |
| `--timezone` | `-tz` | IANA timezone the cron runs in (required with `--cron`) |
| `--assistant` | `-a` | Updated assistant ID (starts with `assistant_`) |
| `--prompt` | `-p` | Updated prompt text |
| `--name` | `-n` | Updated label (`none` to clear it and fall back to the prompt) |
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

Agent thinks: System prompt has `User's timezone: Europe/Zurich`. Local cron is `0 9 * * 1-5`. The assistant is the current one (`$UNIQUE_ASSISTANT_ID`); no need to ask.

Run:
```bash
unique-cli schedule create \
  -c "0 9 * * 1-5" \
  -tz Europe/Zurich \
  -a "$UNIQUE_ASSISTANT_ID" \
  -p "Generate the daily sales report and email it to the team" \
  -n "Daily sales report"
```

Respond: "Done — I created **Daily sales report**, running **every weekday (Mon–Fri) at 9:00 AM your time (Europe/Zurich)**. A new chat will be created for each run."

### Set up a recurring task that continues the same chat

User: "I want to add daily numbers to an existing report chat at 9 AM"

Agent thinks: Already know timezone is Europe/Zurich. Local cron is `0 9 * * 1-5`. Assistant is the current one (`$UNIQUE_ASSISTANT_ID`).

Run:
```bash
unique-cli schedule create \
  -c "0 9 * * 1-5" \
  -tz Europe/Zurich \
  -a "$UNIQUE_ASSISTANT_ID" \
  --chat-id chat_b7ze6mpv0edy324yhjj1d92t \
  -p "Append today's numbers to the running report" \
  -n "Running report top-up"
```

Respond: "Done — I created **Running report top-up**, running **every weekday (Mon–Fri) at 9:00 AM your time**, continuing chat `chat_b7ze6mpv0edy324yhjj1d92t`."

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

Agent thinks: Interval schedule; still pass the known timezone.

Run:
```bash
unique-cli schedule update <task_id> --cron "0 * * * *" --timezone Europe/Zurich
```

Respond: "Updated — the task now runs **every hour**, on the hour."

User: "Actually, make it run at 6:30 PM my time on Fridays"

Agent thinks: Europe/Zurich, local 6:30 PM → cron `30 18 * * 5`.

Run:
```bash
unique-cli schedule update <task_id> --cron "30 18 * * 5" --timezone Europe/Zurich
```

Respond: "Updated — the task now runs **every Friday at 6:30 PM your time**."

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
    timezone="Europe/Zurich",
    assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
    prompt="Generate daily report",
    name="Daily report",
)

# Create (continue existing chat)
task = unique_sdk.ScheduledTask.create(
    user_id="user_123",
    company_id="company_456",
    cronExpression="0 9 * * 1-5",
    timezone="Europe/Zurich",
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

All methods have `*_async` variants for async usage. Omitting `timezone` on create keeps
UTC behaviour for backward compatibility; the CLI always requires it.

## Prerequisites

Requires these environment variables:

```bash
UNIQUE_USER_ID      # User ID (required)
UNIQUE_COMPANY_ID   # Company ID (required)
UNIQUE_ASSISTANT_ID # Current assistant ID — required when an agent uses this
                    # skill. Always pass it as --assistant on schedule create
                    # so the task runs on the same assistant the user is
                    # currently chatting with.
UNIQUE_API_KEY      # API key — optional on localhost / secured cluster
UNIQUE_APP_ID       # App ID — optional on localhost / secured cluster
```

Install: `pip install unique-sdk`
