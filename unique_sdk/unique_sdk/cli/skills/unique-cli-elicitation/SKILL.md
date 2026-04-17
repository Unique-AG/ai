---
name: unique-cli-elicitation
description: >-
  ALWAYS use this skill whenever you would otherwise ask the user a
  question in free-form chat -- for clarifications, confirmations
  (especially destructive actions), missing parameters, multiple-choice
  decisions, or structured form input. Elicitations are routed through
  the Unique AI Platform UI via `unique-cli elicit ask` so the user gets
  a proper structured prompt and you get a structured answer back.
  Do NOT ask the user in plain chat when you can use this skill instead.
---

# Unique CLI -- Elicitation (Ask the User)

Use this skill **whenever you need input from the user** -- a clarifying question, a confirmation before a destructive action, a choice between options, or a structured form. Elicitations create a first-class UI prompt on the Unique AI Platform and return the answer as structured JSON.

> **Rule of thumb:** if you catch yourself about to write "Could you clarify…?" or "Do you want me to…?" or "Which one should I pick?" in chat, stop and call `unique-cli elicit ask` instead.

## When to use

| Situation | Use elicitation? |
|-----------|------------------|
| Clarifying an ambiguous request | Yes |
| Confirming a destructive / irreversible action | Yes, always |
| Picking among 2+ concrete options | Yes |
| Gathering structured data (rating, date, options) | Yes |
| Quick status update / "I'll start now" message | No -- just talk |
| Purely informational output (results, summaries) | No |

## Core Command: `elicit ask`

This is the command you reach for 95% of the time. It creates a FORM elicitation, displays it to the user, and **blocks** until the user answers, declines, cancels, or the request expires.

```bash
unique-cli elicit ask "<question>" [options]
```

### Minimal example (free-text answer)

```bash
unique-cli elicit ask "Which quarter should I report on?"
```

Under the hood this creates a form with a single required string field `answer`. The reply you receive will look like:

```
ID:         elicit_abc123
Status:     RESPONDED
Mode:       FORM
...
Response:   {"answer": "Q1"}
Responded:  2026-04-16 14:22
```

Parse the JSON next to `Response:` to get the user's answer.

### Multiple-choice (recommended for picks / confirmations)

Provide an explicit JSON schema so the user sees proper UI controls instead of a free-text box. Use `enum` for finite choices.

```bash
unique-cli elicit ask "Which report format do you want?" --schema '{
  "type": "object",
  "properties": {
    "format": {
      "type": "string",
      "enum": ["PDF", "DOCX", "Markdown"],
      "description": "Output format"
    }
  },
  "required": ["format"]
}'
```

### Confirmation (destructive action)

Always use this before `rm`, `rmdir -r`, mass uploads, or anything irreversible.

```bash
unique-cli elicit ask "Confirm deleting /Archive/2024 and everything inside it" --schema '{
  "type": "object",
  "properties": {
    "confirm": {
      "type": "boolean",
      "description": "Tick to permanently delete"
    }
  },
  "required": ["confirm"]
}'
```

Proceed **only** if the response contains `"confirm": true`. Treat `DECLINED`, `CANCELLED`, `EXPIRED`, or `confirm: false` all as "do not proceed" -- tell the user you stopped and return control.

### Structured form (multiple fields)

```bash
unique-cli elicit ask "Please provide report settings" --schema '{
  "type": "object",
  "properties": {
    "quarter":   {"type": "string", "enum": ["Q1", "Q2", "Q3", "Q4"]},
    "year":      {"type": "integer", "minimum": 2000, "maximum": 2100},
    "recipients":{"type": "array", "items": {"type": "string", "format": "email"}},
    "include_appendix": {"type": "boolean"}
  },
  "required": ["quarter", "year"]
}'
```

## `elicit ask` Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--tool-name` | `-t` | `agent_question` | Label shown to the user (use a short verb like `clarify`, `confirm`, `choose_report`). |
| `--schema` | | single `answer` string | JSON Schema for the form body. |
| `--chat-id` | `-c` | none | Attach the elicitation to a chat. |
| `--message-id` | `-m` | none | Attach to a specific message. |
| `--expires-in` | | none | Seconds before the request auto-expires. |
| `--timeout` | | `300` | Max seconds to block locally before giving up. |
| `--poll-interval` | | `2.0` | Seconds between status polls. |
| `--metadata` | | none | `key=value` metadata (repeatable). |

## Reading the Response

The command prints a key-value block terminated by:

```
Status:     <TERMINAL_STATUS>
...
Response:   <JSON or "(none)">
```

Terminal statuses:

| Status | Meaning | What to do |
|--------|---------|------------|
| `RESPONDED` / `COMPLETED` | User answered | Parse `Response:` JSON and proceed. |
| `DECLINED` | User explicitly declined | Do not proceed. Acknowledge and stop. |
| `CANCELLED` | Cancelled (by user or system) | Do not proceed. |
| `EXPIRED` | Timed out on the platform (via `--expires-in`) | Ask again only if the task still needs it. |

If the CLI itself times out locally (`elicit: timed out after Ns ...`), the request is still live on the platform -- you can poll later with `elicit wait <id>` or `elicit get <id>`.

## Scripting Pattern

In a shell script or agent tool wrapper, capture the output and pull out the `Response:` line:

```bash
result=$(unique-cli elicit ask "Which region?" --schema '{
  "type":"object",
  "properties":{"region":{"type":"string","enum":["EU","US","APAC"]}},
  "required":["region"]
}')

answer=$(echo "$result" | awk -F'Response:[[:space:]]*' '/^Response:/{print $2}')
region=$(echo "$answer" | jq -r '.region')

case "$region" in
  EU|US|APAC) echo "Proceeding with region=$region";;
  *)          echo "No valid answer ($region); aborting"; exit 1;;
esac
```

## Other Subcommands

These are secondary -- reach for `elicit ask` first.

### `elicit create` -- fire-and-forget

Create without blocking. Useful when you want to ask several things in parallel, or trigger a URL flow.

```bash
# FORM mode
unique-cli elicit create "Please rate the last answer" \
  --mode FORM --tool-name feedback \
  --schema '{"type":"object","properties":{"rating":{"type":"integer","minimum":1,"maximum":5}},"required":["rating"]}'

# URL mode (redirect the user to an external form)
unique-cli elicit create "Complete the onboarding survey" \
  --mode URL --tool-name onboarding --url https://example.com/survey
```

### `elicit pending` -- list open requests

```bash
unique-cli elicit pending
```

### `elicit get <id>` -- snapshot one elicitation

```bash
unique-cli elicit get elicit_abc123
```

### `elicit wait <id>` -- poll until terminal

```bash
unique-cli elicit wait elicit_abc123 --timeout 120
```

### `elicit respond <id>` -- respond programmatically

Mostly for tests / automation. The human user normally responds via the UI.

```bash
unique-cli elicit respond elicit_abc123 --action ACCEPT \
  --content '{"answer":"yes"}'

unique-cli elicit respond elicit_abc123 --action DECLINE
unique-cli elicit respond elicit_abc123 --action CANCEL
```

## Schema Tips

- Always set `"required"` for fields you actually need -- this guarantees the user cannot submit an empty form.
- Use `enum` for closed choices so the UI can render a selector.
- Use `"type": "boolean"` for confirmations; treat `true` as "go ahead", everything else as "stop".
- Add short `description` strings -- they are shown as help text next to each field.
- Keep schemas small. Break long flows into several sequential `elicit ask` calls instead of one giant form.

## Agent Workflow Rules

1. **Default to `elicit ask`.** If you need an answer from the user, use the CLI, not a chat message.
2. **Never run destructive CLI commands without a confirmation elicitation.** This includes `rm`, `rmdir -r`, bulk renames, large uploads, schedule deletion, etc.
3. **Pick a meaningful `--tool-name`.** `confirm_delete`, `choose_region`, `pick_report` -- short snake_case describing the intent.
4. **Constrain answers with a schema** whenever the valid set is finite -- don't rely on parsing free text when `enum` is an option.
5. **Handle non-ACCEPT outcomes explicitly.** If the status is `DECLINED` / `CANCELLED` / `EXPIRED`, tell the user you stopped and ask what they want to do next instead of silently proceeding.
6. **Don't spam elicitations.** One well-designed form with several fields is better than five sequential yes/no questions.
7. **Respect timeouts.** The default `--timeout` is 5 minutes -- raise it only if you genuinely expect the user to take longer.

## Prerequisites

Requires these environment variables:

```bash
UNIQUE_USER_ID    # User ID (required)
UNIQUE_COMPANY_ID # Company ID (required)
UNIQUE_API_KEY    # API key -- optional on localhost / secured cluster
UNIQUE_APP_ID     # App ID -- optional on localhost / secured cluster
```

Install: `pip install unique-sdk`

## SDK Usage (Python)

The CLI is backed by the `unique_sdk.Elicitation` API resource. When scripting from Python you can call it directly instead of shelling out:

```python
import unique_sdk

elicitation = unique_sdk.Elicitation.create_elicitation(
    user_id="user_123",
    company_id="company_456",
    mode="FORM",
    message="Which quarter should I report on?",
    toolName="choose_quarter",
    schema={
        "type": "object",
        "properties": {
            "quarter": {"type": "string", "enum": ["Q1", "Q2", "Q3", "Q4"]}
        },
        "required": ["quarter"],
    },
    expiresInSeconds=600,
)

# Poll until answered
import time
while elicitation["status"] not in {"RESPONDED", "DECLINED", "CANCELLED", "EXPIRED"}:
    time.sleep(2)
    elicitation = unique_sdk.Elicitation.get_elicitation(
        user_id="user_123",
        company_id="company_456",
        elicitation_id=elicitation["id"],
    )

if elicitation["status"] == "RESPONDED":
    print("User picked:", elicitation["responseContent"]["quarter"])
```

All methods have `*_async` variants for async usage.
