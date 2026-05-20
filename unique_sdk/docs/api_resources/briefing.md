# Briefing API

The Briefing API manages the briefing attached to an assistant using the assistant’s identifier (see `/briefings/{assistantId}` in the public OpenAPI specification).

## Overview

Use this API when you need to:

- Read, attach, or update briefing text for a specific assistant (space)
- Detach a briefing from an assistant without deleting the shared record
- Keep assistant briefing content in sync from automation or admin tools

Callers must have permission to manage the target assistant; the server returns `403` when access is denied and `404` when the assistant or briefing attachment does not exist.

With the default [`api_base`](../getting_started/configuration.md) (typically ending in `/public/chat-gen2`), the SDK issues requests under `{api_base}/briefings/{assistantId}`. Override `unique_sdk.api_base` or `UNIQUE_API_BASE` if your deployment uses a different gateway prefix.

## Methods

??? example "`unique_sdk.Briefing.get_for_assistant` - Get briefing for an assistant"

    Returns the briefing attached to the assistant identified by `assistant_id` (`GET /briefings/{assistantId}`).

    **Parameters:**

    - `user_id` (str, required)
    - `company_id` (str, required)
    - `assistant_id` (str, required) — Max length **128** on the API.

    **Returns:** A [`Briefing`](#briefing) instance (`200`).

??? example "`unique_sdk.Briefing.get_for_assistant_async` - Async get"

    Same as **`get_for_assistant`**, but asynchronous.

??? example "`unique_sdk.Briefing.upsert_for_assistant` - Upsert briefing for an assistant"

    Create or update the briefing for the assistant identified by `assistant_id` (`PUT /briefings/{assistantId}`) with a JSON body matching OpenAPI `UpsertBriefingRequestDto`:

    - **`text`** (required, non-empty, max **4000**)
    - **`generatedAt`** (ISO 8601 — if omitted or blank, the SDK sends current UTC time)
    - **`prompts`** (required list, max **200**; each item: **`title`** max **100**, **`body`** max **4000**)
    - **`title`** (optional display title, max **100**)

    **Parameters:**

    - `user_id`, `company_id`, `assistant_id` (required)
    - `text`, `generatedAt`, `prompts`, `title` — see above
    - `markdown` / `content` — Legacy aliases sent as **`text`**

    **Returns:** A [`Briefing`](#briefing) instance (`200`).

    **Example:**

    ```python
    briefing = unique_sdk.Briefing.upsert_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_external_id,
        text="# Role\nAssist users with onboarding...",
        title="Today's Briefing",
        generatedAt="2026-04-29T06:46:06.789Z",
        prompts=[
            {"title": "First idea", "body": "Ask about priorities."},
        ],
    )
    ```

??? example "`unique_sdk.Briefing.upsert_for_assistant_async` - Async upsert"

    Same behavior as **`upsert_for_assistant`**, but asynchronous.

??? example "`unique_sdk.Briefing.detach_for_assistant` - Detach briefing from an assistant"

    Removes the briefing attachment for the assistant (`DELETE /briefings/{assistantId}`). The underlying briefing record is preserved when other assistants in the tenant still reference it.

    **Returns:** A [`DetachResult`](#detachresult) (`200`).

??? example "`unique_sdk.Briefing.detach_for_assistant_async` - Async detach"

    Same as **`detach_for_assistant`**, but asynchronous.

## Input and return types

#### UpsertForAssistantParams {#upsertforassistantparams}

??? note "Request body (`UpsertBriefingRequestDto`)"

    - `text`, `generatedAt`, `prompts` — Required on the wire (see upsert method above).
    - `title` — Optional display title (max **100**).
    - `markdown` / `content` — Legacy aliases mapped to **`text`**.

    Per-call `api_key`, `api_base`, and `headers` are transport-only and not sent in the JSON body.

#### Briefing {#briefing}

??? note "The `Briefing` resource object (`BriefingDto`)"

    - `object` — `"briefing"`
    - `externalId` — Stable external identifier (assistant id when attached per-assistant)
    - `text`, `generatedAt`, `title`, `createdAt`, `updatedAt`
    - `prompts` — List of `BriefingPromptDto` rows (`id`, `title`, `body`, `order`, timestamps)

    Legacy fields such as `assistantId` or `id` may still appear depending on API version.

    **Returned by:** `get_for_assistant()`, `upsert_for_assistant()` (+ async variants)

#### DetachResult {#detachresult}

??? note "Detach response (`DeleteBriefingResultDto`)"

    - `object` — `"deleted-briefing"`
    - `id` — Echoes the `assistantId` from the URL
    - `deleted` — Whether the detach succeeded

    **Returned by:** `detach_for_assistant()` (+ async variant)

## HTTP status semantics

| Code | Typical cause |
| --- | --- |
| `200` | Success |
| `400` | Invalid parameters |
| `401` | Missing or invalid authentication |
| `403` | Insufficient access to the assistant |
| `404` | Assistant or briefing attachment not found |
| `422` | Upstream service error |

## Related resources

- [Space API](space.md) — Create and configure assistants (spaces)
