# Elicitation

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

Ask the user a structured question and get a typed answer back. Elicitations are first-class user-input requests routed through the Unique AI Platform UI -- use them instead of asking in free-form chat whenever you need a clarification, a confirmation (especially before a destructive action), a choice between options, or a small structured form.

The CLI exposes the full lifecycle:

- `elicit ask` -- **create + wait** in a single call (the one you usually want)
- `elicit create` -- fire-and-forget create (FORM or URL mode)
- `elicit pending` -- list open requests for the current user
- `elicit get` -- fetch one elicitation by ID
- `elicit wait` -- poll an existing elicitation until it reaches a terminal state
- `elicit respond` -- respond on behalf of the user (scripting / tests)

Elicitations move through these statuses:

| Status | Meaning |
|--------|---------|
| `PENDING` | Created, waiting for a response |
| `RESPONDED` / `COMPLETED` | The user submitted an answer (`responseContent` is populated) |
| `DECLINED` | The user explicitly declined |
| `CANCELLED` | Cancelled by the user or system |
| `EXPIRED` | Not answered before `expiresAt` |

Any status other than `PENDING` is **terminal** -- `elicit wait` returns as soon as one of these is reached.

---

## elicit ask

Create a FORM elicitation and block until the user responds, declines, cancels, expires, or the local `--timeout` elapses. This is the idiomatic way for an agent to request input from the user.

**Synopsis:**

```
elicit ask <message> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `message` | The question or instruction shown to the user |

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--tool-name` | `-t` | `agent_question` | Short tool/intent label shown in the UI (e.g. `confirm_delete`, `choose_quarter`). |
| `--schema` | | single required `answer` string | JSON Schema for the form body. |
| `--chat-id` | `-c` | none | Attach the elicitation to a chat. |
| `--message-id` | `-m` | none | Attach to a specific message. |
| `--expires-in` | | none | Seconds before the platform auto-expires the request. |
| `--timeout` | | `300` | Max seconds to block locally while polling. |
| `--poll-interval` | | `2.0` | Seconds between polls. |
| `--metadata` | | none | `key=value` metadata (repeatable). |
| `--visible` / `--no-visible` | | `--visible` | Wrap the elicitation in a synthetic "thinking" timeline so the chat UI renders it (UN-19815 workaround). |
| `--assistant-id` | | `$UNIQUE_ASSISTANT_ID`, else latest assistant in chat | Assistant id for the visibility placeholder. |
| `--placeholder-text` | | `Waiting for your answer…` | Text on the placeholder thinking step. |
| `--cleanup` | | `collapse` | How to tear down the placeholder afterwards (`collapse` \| `delete`). |

!!! note "UN-19815 visibility workaround"
    As of April 2026, the chat UI only renders an elicitation when its host
    assistant message is actively in the *thinking timeline* display mode.
    Elicitations emitted against a chat without a live streaming turn are
    stored correctly by the backend but are silently invisible in the UI.
    When you pass `--chat-id`, the CLI now (by default) materialises a
    short-lived placeholder assistant message and running step so the UI
    has somewhere to render the card; the placeholder is collapsed or
    deleted automatically when the user responds. Pass `--no-visible` to
    opt out once the permanent UI fix (ticket UN-19815) has landed in your
    environment.

**Default schema (when `--schema` is omitted):**

```json
{
  "type": "object",
  "properties": {
    "answer": {
      "type": "string",
      "description": "Free-text answer to the question."
    }
  },
  "required": ["answer"]
}
```

**Examples:**

```bash
# Free-text question
unique-cli elicit ask "Which quarter should I report on?"

# Multiple choice -- use `enum` so the UI renders a selector
unique-cli elicit ask "Pick a region" --tool-name choose_region --schema '{
  "type": "object",
  "properties": {
    "region": {"type": "string", "enum": ["EU", "US", "APAC"]}
  },
  "required": ["region"]
}'

# Confirmation before a destructive action
unique-cli elicit ask "Confirm permanently deleting /Archive/2024 and all its contents" \
  --tool-name confirm_delete \
  --timeout 120 \
  --schema '{
    "type": "object",
    "properties": {"confirm": {"type": "boolean"}},
    "required": ["confirm"]
  }'
```

**Sample output:**

```
ID:         elicit_9a7b
Status:     RESPONDED
Mode:       FORM
Source:     INTERNAL_TOOL
Tool:       choose_region
Message:    Pick a region
Schema:     {"type":"object","properties":{"region":{"type":"string","enum":["EU","US","APAC"]}},"required":["region"]}
URL:        -
Chat:       -
Message ID: -
External ID: -
Metadata:   -
Response:   {"region": "EU"}
Responded:  2026-04-16 14:22
Expires:    -
Created:    2026-04-16 14:21
Updated:    2026-04-16 14:22
```

Agents parse the JSON after `Response:` to get the structured answer.

!!! tip "Scripting"
    Extract the response with `awk` + `jq`:

    ```bash
    out=$(unique-cli elicit ask "Pick a region" --schema '...')
    json=$(echo "$out" | awk -F'Response:[[:space:]]*' '/^Response:/{print $2}')
    region=$(echo "$json" | jq -r '.region')
    ```

---

## elicit create

Create an elicitation without waiting for the response. Useful when you want to ask several things in parallel or trigger a URL-based flow.

**Synopsis:**

```
elicit create <message> --mode FORM|URL --tool-name <name> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `message` | The question or instruction shown to the user |

**Options:**

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--mode` | | Yes | `FORM` (render a JSON Schema form) or `URL` (redirect to an external page) |
| `--tool-name` | `-t` | Yes | Short tool/intent label |
| `--schema` | | FORM | JSON Schema for the form body (required when `--mode FORM`) |
| `--url` | | URL | External URL (required when `--mode URL`) |
| `--chat-id` | `-c` | No | Associated chat ID |
| `--message-id` | `-m` | No | Associated message ID |
| `--expires-in` | | No | Auto-expire after N seconds |
| `--external-id` | | No | External identifier for de-duplication / tracking |
| `--metadata` | | No | `key=value` metadata (repeatable) |

**Examples:**

```bash
# Fire-and-forget FORM elicitation
unique-cli elicit create "Please rate the last answer" \
  --mode FORM --tool-name feedback \
  --schema '{"type":"object","properties":{"rating":{"type":"integer","minimum":1,"maximum":5}},"required":["rating"]}'

# URL elicitation -- the user is redirected to an external survey
unique-cli elicit create "Complete the onboarding survey" \
  --mode URL --tool-name onboarding \
  --url https://example.com/survey?user=123
```

The command prints the created elicitation (including its `ID:`), which you can then feed into `elicit wait` / `elicit get`.

---

## elicit pending

List all pending (unanswered, unexpired) elicitations for the authenticated user.

**Synopsis:**

```
elicit pending
```

**Example:**

```bash
unique-cli elicit pending
```

```
2 pending elicitation(s):

STATUS    MODE  TOOL           MESSAGE                              ID           EXPIRES
PENDING   FORM  choose_region  Pick a region                        elicit_9a7b  2026-04-16 14:40
PENDING   URL   onboarding     Complete the onboarding survey       elicit_42cd  -
```

---

## elicit get

Show the full details of a single elicitation by ID.

**Synopsis:**

```
elicit get <elicitation_id>
```

**Example:**

```bash
unique-cli elicit get elicit_9a7b
```

Output is the same key-value block as `elicit ask` (minus the blocking behavior). Use this to inspect an elicitation's current `Status:` and `Response:` at any time.

---

## elicit wait

Poll an existing elicitation until it reaches a terminal state or the local timeout elapses.

**Synopsis:**

```
elicit wait <elicitation_id> [--timeout <seconds>] [--poll-interval <seconds>]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--timeout` | `300` | Max seconds to wait for a terminal state |
| `--poll-interval` | `2.0` | Seconds between polls |

**Example:**

```bash
unique-cli elicit wait elicit_9a7b --timeout 120
```

On timeout, the CLI prints `elicit: timed out after Ns waiting for <id> (last status: PENDING)` followed by the last observed snapshot. The elicitation remains live on the platform -- call `elicit wait` again to resume.

---

## elicit respond

Respond to an elicitation. The user normally does this via the Unique UI; the CLI path is mostly for scripting, integration tests, and declining / cancelling on behalf of the user.

**Synopsis:**

```
elicit respond <elicitation_id> --action ACCEPT|DECLINE|CANCEL [--content <json>]
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--action` | Yes | Response action: `ACCEPT`, `DECLINE`, or `CANCEL` |
| `--content` | for `ACCEPT` | JSON object matching the elicitation's schema |

**Examples:**

```bash
# Accept with content (simulate a user answer in a test)
unique-cli elicit respond elicit_9a7b --action ACCEPT \
  --content '{"region":"EU"}'

# Decline or cancel
unique-cli elicit respond elicit_9a7b --action DECLINE
unique-cli elicit respond elicit_9a7b --action CANCEL
```

---

## End-to-End Example

```bash
# 1. Create the question, fire-and-forget
ID=$(unique-cli elicit create "Which quarter?" \
       --mode FORM --tool-name choose_quarter \
       --schema '{"type":"object","properties":{"q":{"type":"string","enum":["Q1","Q2"]}},"required":["q"]}' \
     | awk '/^ID:/{print $2}')

# 2. Block until answered (could be a different terminal or process)
unique-cli elicit wait "$ID" --timeout 300
```

For the common case of "ask and immediately use the answer", `elicit ask` collapses steps 1 and 2 into a single command.

---

## Schema Guidance

- Always set `"required"` on fields that must be present -- this prevents empty submissions.
- Use `"enum"` for finite choices so the UI renders a selector instead of a free-text box.
- Use `"type": "boolean"` for yes/no confirmations -- treat `true` as "go ahead" and anything else (including `DECLINED` / `CANCELLED` / `EXPIRED` statuses) as "stop".
- Add short `"description"` strings -- they appear as helper text next to each field.
- Keep schemas small. Several sequential `elicit ask` calls are usually clearer than one giant form.

## Handling Non-Response Outcomes

After `elicit ask` / `elicit wait` returns, always branch on the `Status:` value:

| Status | Typical action |
|--------|----------------|
| `RESPONDED` / `COMPLETED` | Parse `Response:` JSON and proceed with the task. |
| `DECLINED` | Stop. Acknowledge to the user that you stopped and ask what to do next. |
| `CANCELLED` | Stop. The user (or system) aborted the flow. |
| `EXPIRED` | The request timed out platform-side. Decide whether to re-ask. |
| `elicit: timed out ...` (CLI only) | Local wait exceeded `--timeout`. The request is still live on the platform -- poll again with `elicit wait <id>` later. |

## Related

- [Elicitation API Reference](../api_resources/elicitation.md) -- Python SDK methods, return types, and async variants
- [Command Reference](commands.md) -- All CLI commands
- [Scheduled Tasks](scheduled_tasks.md) -- Another long-running platform workflow managed via the CLI
