# Elicitation

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

Ask the user a structured question and get a typed answer back. Elicitations are first-class user-input requests routed through the Unique AI Platform UI -- use them instead of asking in free-form chat whenever you need a clarification, a confirmation (especially before a destructive action), a choice between options, or a small structured form.

The CLI exposes the full lifecycle:

- `elicit ask` -- **create + wait** in a single call
- `elicit create` -- fire-and-forget create (FORM or URL mode)
- `elicit pending` -- list open requests for the current user
- `elicit get` -- fetch one elicitation by ID
- `elicit wait` -- poll an existing elicitation until it reaches a terminal state
- `elicit respond` -- respond on behalf of the user (scripting / tests)

### Choosing between `ask` and `create` + `wait`

`elicit ask` and `elicit create` + `elicit wait` are two ways to get the same
answer -- **which one to use depends on your calling context**, not a fixed
rule of this doc:

- **`elicit ask`** is the right choice for a single blocking call: scripts,
  tests, ops usage, or an agent environment whose instructions say it
  supervises long-running tool calls (does not silently background or kill
  the process before a human answers).
- **`elicit create` + a short polling loop with `elicit wait`** is the right
  choice when the caller cannot safely block for the full wait in one call --
  e.g. most agent harnesses, whose Bash/shell tool has its own short
  foreground-wait timeout. See the [`unique-cli-elicitation` skill's "Two
  patterns" section](../../unique_sdk/cli/skills/unique-cli-elicitation/SKILL.md)
  for the agent-facing version of this guidance, including which one to
  default to when instructions are silent.

Elicitations move through these statuses:

| Status | Meaning |
|--------|---------|
| `PENDING` | Created, waiting for a response |
| `RESPONDED` / `ACCEPTED` / `COMPLETED` | The user submitted an answer, or accepted an empty-schema confirmation (`responseContent` is populated for `RESPONDED`/`COMPLETED`) |
| `DECLINED` / `REJECTED` | The user explicitly declined, or rejected an empty-schema confirmation |
| `CANCELLED` | Cancelled by the user or system |
| `EXPIRED` | Not answered before `expiresAt` (`--expires-in`, or `--timeout` if `--expires-in` was not passed) |

`ACCEPTED`/`REJECTED` are accept/decline synonyms for `RESPONDED`/`DECLINED`
produced by some response paths (e.g. the Codex approval-bridge integration);
treat them identically (`ACCEPTED` → proceed, `REJECTED` → stop).

Any status other than `PENDING` is **terminal** -- `elicit wait` returns as soon as one of these is reached. A non-terminal (`PENDING`) result -- including a local `--timeout` being reached while the platform-side request is still open -- is never itself a decline, cancellation, or answer; it only ever means "keep waiting."

---

## elicit ask

Create a FORM elicitation and block until the user responds, declines, cancels, expires, or the local `--timeout` elapses. This is the idiomatic single-call way to request input from the user -- appropriate for scripts, tests, ops usage, and agent environments that supervise long-running tool calls (see "Choosing between `ask` and `create` + `wait`" above).

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
| `--expires-in` | | `--timeout`'s value | Seconds before the platform auto-expires the request, decoupled from `--timeout`. See "Decoupling expiry from the local wait" below. |
| `--timeout` | | `7200` | Max seconds to block locally while polling. |
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

# Confirmation before a destructive action: empty-properties schema —
# the Confirm/Cancel buttons are the consent; gate on Status: ACCEPTED
unique-cli elicit ask "Permanently delete /Archive/2024 and all its contents? Confirming deletes it immediately — this cannot be undone." \
  --tool-name confirm_delete \
  --timeout 120 \
  --schema '{"type": "object", "properties": {}}'
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

### Decoupling expiry from the local wait

By default `ask` has a single knob: `--timeout` is both how long this process
blocks polling *and* when the elicitation expires on the platform (it sends
`--timeout`'s value as the server-side `expiresIn`). That coupling exists so
the backend's short default expiry never leaves a record `PENDING` after the
CLI has already stopped waiting.

Pass `--expires-in` to decouple the two:

```bash
# Elicitation stays live on the platform for 2 hours even though this
# process only waits 5 minutes before returning a "still PENDING" result.
unique-cli elicit ask "Approve this change?" --expires-in 7200 --timeout 300
```

Use this when the caller's own wait budget is shorter than how long a human
should realistically have to answer -- e.g. a harness with its own
foreground-wait timeout. Without `--expires-in`, the request would expire
under the user at the low `--timeout` value before they ever see it; with
it, the request outlives the process and a later `elicit wait <id>` call (or
another `ask`-style re-poll) can still pick up the answer. Omitting
`--expires-in` reproduces exactly today's coupled behavior.

### Elicitation-created stderr line

Immediately after `ask` creates the elicitation -- before it starts polling
-- it writes one line to **stderr** (never stdout):

```
UNIQUE_ELICITATION_CREATED id=<id> expires_at=<iso8601>
```

This is a stable, greppable, machine-readable line intended for callers
(harnesses, wrapper scripts) that want the elicitation id the instant it
exists, instead of polling `elicit pending` to discover it. It does not
change `ask`'s stdout output in any way.

### Transient-failure retries

While polling, `ask` (via the same `cmd_elicit_wait` logic used by the
standalone `elicit wait` command) retries transient failures -- connection
errors, timeouts, and 5xx responses -- with bounded exponential backoff,
instead of ending the wait on the first dropped connection. Each retry is
logged to stderr with the attempt number and backoff delay. 4xx errors are
not retried (they cannot succeed on retry). Retries are always bounded by
the overall `--timeout` (or, for the standalone `elicit wait` command, the
`--timeout` passed to it) -- a persistent failure still gives up once that
budget is exhausted, returning the same `elicit: <error>` output as before
this retry logic existed.

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
elicit create <message> [--mode FORM|URL] --tool-name <name> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `message` | The question or instruction shown to the user |

**Options:**

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--mode` | | No (default `FORM`) | `FORM` (render a JSON Schema form) or `URL` (redirect to an external page) |
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
| `--timeout` | `7200` | Max seconds to wait for a terminal state |
| `--poll-interval` | `2.0` | Seconds between polls |

**Example:**

```bash
unique-cli elicit wait elicit_9a7b --timeout 120
```

On timeout, the CLI prints `elicit: still PENDING after Ns waiting for <id> (last status: PENDING) — this is NOT a stopping condition`, followed by an explicit `elicit wait` invocation to run again and the last observed snapshot. The elicitation remains live on the platform -- call `elicit wait` again to resume; a non-terminal timeout is never itself a reason to stop.

Transient failures while polling (connection errors, timeouts, 5xx) are retried with bounded exponential backoff, logged to stderr, and bounded by the overall `--timeout` -- see "Transient-failure retries" under `elicit ask` above for details (the retry logic is shared between `ask` and `wait`).

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
unique-cli elicit wait "$ID" --timeout 7200
```

For the common case of "ask and immediately use the answer", `elicit ask` collapses steps 1 and 2 into a single command.

---

## Schema Guidance

- Always set `"required"` on fields that must be present -- this prevents empty submissions.
- Use `"enum"` for finite choices so the UI renders a selector instead of a free-text box.
- For pure yes/no confirmations use an empty-properties schema (`{"type": "object", "properties": {}}`) and gate on `Status: ACCEPTED` -- do **not** add a boolean `confirm` field. The UI's Confirm button and a checkbox are two separate signals: a user can press Confirm with the box unchecked, showing **Accepted** in the UI while the response carries `confirm: false`. Treat `DECLINED` / `REJECTED` / `CANCELLED` / `EXPIRED` as "stop". Reserve `"type": "boolean"` for genuine data fields where `false` is a valid submittable answer.
- Add short `"description"` strings -- they appear as helper text next to each field.
- Keep schemas small. Several sequential `elicit ask` calls are usually clearer than one giant form.

## Handling Non-Response Outcomes

After `elicit ask` / `elicit wait` returns, always branch on the `Status:` value:

| Status | Typical action |
|--------|----------------|
| `RESPONDED` / `ACCEPTED` / `COMPLETED` | Parse `Response:` JSON and proceed with the task (`ACCEPTED` is the accept-synonym produced by some response paths; treat it like `RESPONDED`). |
| `DECLINED` / `REJECTED` | Stop. Acknowledge to the user that you stopped and ask what to do next (`REJECTED` is the decline-synonym produced by some response paths; treat it like `DECLINED`). |
| `CANCELLED` | Stop. The user (or system) aborted the flow. |
| `EXPIRED` | The request timed out platform-side. Decide whether to re-ask. |
| `elicit: still PENDING after Ns ...` / `elicit: timed out after Ns ...` (CLI only) | Local wait exceeded `--timeout`. This is **not** a stopping condition and **not** the same as `EXPIRED` -- the request is still live on the platform (until its own `expiresAt`); call `elicit wait <id>` again immediately. |

## Related

- [`unique-cli-elicitation` skill](../../unique_sdk/cli/skills/unique-cli-elicitation/SKILL.md) -- Agent-facing guidance, including which of `ask` vs `create` + `wait` to default to
- [Elicitation API Reference](../api_resources/elicitation.md) -- Python SDK methods, return types, and async variants
- [Command Reference](commands.md) -- All CLI commands
- [Scheduled Tasks](scheduled_tasks.md) -- Another long-running platform workflow managed via the CLI
