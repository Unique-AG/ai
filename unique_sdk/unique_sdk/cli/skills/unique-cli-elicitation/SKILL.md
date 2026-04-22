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

!!! danger "`--visible` is currently MANDATORY"
    You **must always run `elicit ask` with visibility on** (it is on by default — just don't pass `--no-visible`). Until the UN-19815 UI fix ships in your environment, an elicitation created without the visibility workaround is stored by the backend but **never rendered in the chat UI** — the user simply never sees the question and you will wait forever. There is no situation in which you should disable it today.

## The only command you need: `elicit ask`

`elicit ask` is a **single call that creates the elicitation, shows it to the user, and blocks until the user answers** (or declines / cancels / expires). This is the command you reach for every time. You do not need to learn `elicit create`, `elicit wait`, `elicit pending`, `elicit get`, or `elicit respond` — they exist for scripting and tests, not for agent workflows.

```bash
unique-cli elicit ask "<question>" [options]
```

!!! danger "`--chat-id` and `--message-id` are MANDATORY"
    You **must always pass both** `--chat-id "$UNIQUE_CHAT_ID"` **and** `--message-id "$UNIQUE_MESSAGE_ID"` on every `elicit ask` call. These environment variables are always available in the agent environment. Without both flags the elicitation is not correctly anchored to the current conversation and the user will not see it.

## When to use

| Situation | Use elicitation? |
|-----------|------------------|
| Clarifying an ambiguous request | Yes |
| Confirming a destructive / irreversible action | Yes, always |
| Picking among 2+ concrete options | Yes |
| Gathering structured data (rating, date, options) | Yes |
| Quick status update / "I'll start now" message | No -- just talk |
| Purely informational output (results, summaries) | No |

## Examples

### Minimal — free-text answer

```bash
unique-cli elicit ask "Which quarter should I report on?" \
  --chat-id "$UNIQUE_CHAT_ID" \
  --message-id "$UNIQUE_MESSAGE_ID"
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
unique-cli elicit ask "Which report format do you want?" \
  --chat-id "$UNIQUE_CHAT_ID" \
  --message-id "$UNIQUE_MESSAGE_ID" \
  --schema '{
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
unique-cli elicit ask "Confirm deleting /Archive/2024 and everything inside it" \
  --chat-id "$UNIQUE_CHAT_ID" \
  --message-id "$UNIQUE_MESSAGE_ID" \
  --schema '{
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
unique-cli elicit ask "Please provide report settings" \
  --chat-id "$UNIQUE_CHAT_ID" \
  --message-id "$UNIQUE_MESSAGE_ID" \
  --schema '{
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

## Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--chat-id` | `-c` | none | **MANDATORY.** Chat to show the question in. Always pass `"$UNIQUE_CHAT_ID"`. Without it the visibility workaround cannot run and the user will not see the elicitation. |
| `--message-id` | `-m` | none | **MANDATORY.** The current assistant message ID. Always pass `"$UNIQUE_MESSAGE_ID"`. Anchors the elicitation to the correct message in the conversation thread. |
| `--tool-name` | `-t` | `agent_question` | Short snake_case label shown to the user (e.g. `clarify`, `confirm_delete`, `choose_report`). |
| `--schema` | | single `answer` string | JSON Schema for the form body. |
| `--expires-in` | | none | Seconds before the request auto-expires on the platform. |
| `--timeout` | | `300` | Max seconds to block locally before giving up. |
| `--poll-interval` | | `2.0` | Seconds between status polls. |
| `--metadata` | | none | `key=value` metadata (repeatable). |
| `--assistant-id` | | `$UNIQUE_ASSISTANT_ID`, else latest assistant in chat | Assistant id for the placeholder message created by the visibility workaround. Set this (or export `UNIQUE_ASSISTANT_ID`) only if the chat is brand-new with no prior assistant messages. |

!!! danger "Never pass `--no-visible`"
    The visibility workaround is on by default. **Do not pass `--no-visible`.** Without it the elicitation is invisible in the chat UI, the user never answers, and `elicit ask` blocks until `--timeout`. This is true in every environment today — there is no correct use of `--no-visible` from an agent.

## Reading the response

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

If the CLI itself times out locally (`elicit: timed out after Ns ...`), raise `--timeout` and try again. If this happens repeatedly, double-check that you passed `--chat-id` and did not pass `--no-visible` — an invisible elicitation is the most common cause of a local timeout.

## Scripting pattern

In a shell script or agent tool wrapper, capture the output and pull out the `Response:` line:

```bash
result=$(unique-cli elicit ask "Which region?" \
  --chat-id "$UNIQUE_CHAT_ID" \
  --message-id "$UNIQUE_MESSAGE_ID" \
  --schema '{
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

## Schema tips

- Always set `"required"` for fields you actually need -- this guarantees the user cannot submit an empty form.
- Use `enum` for closed choices so the UI can render a selector.
- Use `"type": "boolean"` for confirmations; treat `true` as "go ahead", everything else as "stop".
- Add short `description` strings -- they are shown as help text next to each field.
- Keep schemas small. Break long flows into several sequential `elicit ask` calls instead of one giant form.

## Agent workflow rules

1. **Default to `elicit ask`.** If you need an answer from the user, use this command, not a chat message. Do not use any of the other `elicit *` subcommands from an agent.
2. **Always pass `--chat-id "$UNIQUE_CHAT_ID"`.** Without it the elicitation is not attached to a chat and the user will not see it.
3. **Always pass `--message-id "$UNIQUE_MESSAGE_ID"`.** This anchors the elicitation to the current message in the conversation. Both `$UNIQUE_CHAT_ID` and `$UNIQUE_MESSAGE_ID` are always available as environment variables — never omit either.
4. **Never pass `--no-visible`.** See the warning above. The visibility workaround is mandatory today.
5. **Never run destructive CLI commands without a confirmation elicitation.** This includes `rm`, `rmdir -r`, bulk renames, large uploads, schedule deletion, etc.
6. **Pick a meaningful `--tool-name`.** `confirm_delete`, `choose_region`, `pick_report` -- short snake_case describing the intent.
7. **Constrain answers with a schema** whenever the valid set is finite -- don't rely on parsing free text when `enum` is an option.
8. **Handle non-`RESPONDED` outcomes explicitly.** If the status is `DECLINED` / `CANCELLED` / `EXPIRED`, tell the user you stopped and ask what they want to do next instead of silently proceeding.
9. **Don't spam elicitations.** One well-designed form with several fields is better than five sequential yes/no questions.
10. **Respect timeouts.** The default `--timeout` is 5 minutes -- raise it only if you genuinely expect the user to take longer.

## Prerequisites

Requires these environment variables:

```bash
UNIQUE_USER_ID    # User ID (required)
UNIQUE_COMPANY_ID # Company ID (required)
UNIQUE_API_KEY    # API key -- optional on localhost / secured cluster
UNIQUE_APP_ID     # App ID -- optional on localhost / secured cluster
UNIQUE_CHAT_ID    # Current chat ID -- always pass as --chat-id (required)
UNIQUE_MESSAGE_ID # Current message ID -- always pass as --message-id (required)
```

Install: `pip install unique-sdk`
