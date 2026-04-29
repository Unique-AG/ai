# Briefing API

The Briefing API creates or replaces the briefing attached to an assistant using the assistant’s identifier. The API upserts the briefing with that id as its external id (see `PUT /briefings/{assistantId}` and `#/components/schemas/PublicUpsertBriefingRequestDto` in the public OpenAPI specification).

## Overview

Use this API when you need to:

- Attach or update briefing text for a specific assistant (space)
- Keep assistant briefing content in sync from automation or admin tools

Callers must have permission to manage the target assistant; the server returns `403` when access is denied and `404` when the assistant does not exist.

With the default [`api_base`](../getting_started/configuration.md) (typically ending in `/public/chat-gen2`), the SDK issues `PUT {api_base}/briefings/{assistantId}` — for example `https://gateway.example/public/chat-gen2/briefings/assistant_…`. Override `unique_sdk.api_base` or `UNIQUE_API_BASE` if your deployment uses a different gateway prefix.

## Methods

??? example "`unique_sdk.Briefing.upsert_for_assistant` - Upsert briefing for an assistant"

    Create or update the briefing for the assistant identified by `assistant_id`. The HTTP request is `PUT /briefings/{assistantId}` with a JSON body matching OpenAPI `PublicUpsertBriefingRequestDto`: **`text`** (required, non-empty string, max length **4000**), **`generatedAt`** (ISO 8601 date/time — if omitted or blank, the SDK sends current UTC time), and **`prompts`** (required list, max **200** items; each item has **`title`** max **100** and **`body`** max **4000** characters — this is the full replacement set persisted in order).

    **Parameters:**

    - `user_id` (str, required) — Authenticated user id (forwarded via `x-user-id`).
    - `company_id` (str, required) — Company scope (forwarded via `x-company-id`).
    - `assistant_id` (str, required) — Assistant the briefing attaches to (path segment; URI-encoded when necessary). Matches OpenAPI path `assistantId` (max length **128**).
    - `text` (str, required unless legacy aliases below are used) — Briefing body. Must be ≤ 4000 characters.
    - `generatedAt` (str, optional) — Timestamp for this briefing revision in ISO 8601. If omitted or blank, the SDK sends the **current UTC** time (recommended for automated updates).
    - `prompts` (list, required) — Full replacement list of prompts (max **200**). Each element is ``{"title": str, "body": str}``. Pass ``[]`` to clear prompts on the server.
    - `markdown` (str, optional) — Legacy alias; sent as **`text`** in JSON.
    - `content` (str, optional) — Legacy alias; sent as **`text`** in JSON.

    **Returns:**

    Returns a [`Briefing`](#briefing) instance (`200`).

    **Example:**

    ```python
    briefing = unique_sdk.Briefing.upsert_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_external_id,
        text="# Role\nAssist users with onboarding...",
        generatedAt="2026-04-29T06:46:06.789Z",
        prompts=[
            {"title": "First idea", "body": "Ask about priorities."},
            {"title": "Follow-up", "body": "Summarize next steps."},
        ],
    )
    print(f"Briefing id: {briefing['id']} assistant={briefing['assistantId']}")
    ```

??? example "`unique_sdk.Briefing.upsert_for_assistant_async` - Async upsert"

    Same behavior as **`upsert_for_assistant`** above, but asynchronous.

    **Parameters:**

    Same as the synchronous method.

    **Returns:**

    Returns a [`Briefing`](#briefing) instance.

    **Example:**

    ```python
    briefing = await unique_sdk.Briefing.upsert_for_assistant_async(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_external_id,
        text="Updated briefing text.",
        prompts=[],
    )
    ```

## Input and return types

#### UpsertForAssistantParams {#upsertforassistantparams}

??? note "Request body (`PublicUpsertBriefingRequestDto`)"

    Keyword arguments become the JSON object sent as `application/json`.

    **Fields:**

    - `text` (str) — Primary field for briefing body (**max 4000** characters on the API).
    - `generatedAt` (str, optional) — ISO 8601 string; omitted or empty → SDK uses current UTC.
    - `prompts` (list of `{title, body}`) — Required on the wire. Max **200** entries; **`title`** max **100**, **`body`** max **4000** characters each.
    - `markdown` / `content` — Optional legacy aliases mapped to **`text`** before sending.

    Optional per-call overrides (`api_key`, `api_base`, `headers`) apply to SDK transport only and are **not** included in the JSON body; see [Configuration](../getting_started/configuration.md) for global defaults.

#### Briefing {#briefing}

??? note "The `Briefing` resource object"

    **Typical fields (aligned with `#/components/schemas/PublicBriefingDto` where exposed):**

    - `id` (str) — Briefing identifier
    - `object` (str) — Often `"briefing"` for typed SDK responses
    - `assistantId` (str) — Assistant this briefing is attached to
    - `text` (str, optional) — Stored briefing body when returned
    - `generatedAt` (str, optional) — Generation timestamp (ISO 8601) when returned
    - `prompts` (list, optional) — Ordered prompt rows when returned (see `PublicBriefingPromptDto`)
    - `content` / `markdown` — May appear depending on API version
    - `title` (str, optional) — If exposed by the API
    - `createdAt`, `updatedAt` (str, optional)

    **Returned by:** `upsert_for_assistant()`, `upsert_for_assistant_async()`

## HTTP status semantics

The underlying route can return:

- `200` — Briefing created or updated and attached to the assistant.
- `400` — Invalid request parameters (e.g. empty `text`, invalid `generatedAt`).
- `401` — Missing or invalid authentication.
- `403` — Caller lacks manage access to the assistant.
- `404` — Assistant not found.
- `422` — Request could not be processed due to an upstream service error.

## Related resources

- [Space API](space.md) — Create and configure assistants (spaces)
