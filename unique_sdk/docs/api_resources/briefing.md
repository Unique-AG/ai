# Briefing API

The Briefing API manages the briefing attached to an assistant using the assistant’s identifier (see `PUT /briefings/{assistantId}` and `#/components/schemas/PublicUpsertBriefingRequestDto` in the public OpenAPI specification).

## Overview

Use this API when you need to:

- Read, attach, or update briefing text for a specific assistant (space)
- Remove a briefing attachment from an assistant (the shared record may remain)
- Keep assistant briefing content in sync from automation or admin tools

Callers must have permission to manage the target assistant; the server returns `403` when access is denied and `404` when the assistant or briefing attachment does not exist.

Briefings are served on the **unique-api** gateway surface (see QA OpenAPI at `https://gateway.qa.unique.app/unique-api/openapi.json`). Set `unique_sdk.api_base` (or `UNIQUE_API_BASE` / `UNIQUE_API_BASE_URL`) to your gateway prefix ending in **`/unique-api`**, e.g. `https://gateway.unique.app/unique-api` — not `/public/chat-gen2` and not the bare gateway host alone.

## Example: create, retrieve, and delete

Runnable script: [`examples/basics/briefing_crud.py`](../../examples/basics/briefing_crud.py) (SDK setup via [`sdk_env.py`](../../examples/basics/sdk_env.py) → `unique_sdk.cli.config.load_config`; not shipped in the PyPI wheel). Add `examples/basics/.env` with `UNIQUE_*` credentials, `ASSISTANT_ID`, and `UNIQUE_API_BASE_URL` (a bare `https://gateway…` host is auto-suffixed with `/unique-api` in the example helper). From the `unique_sdk` directory:

```bash
uv run python examples/basics/briefing_crud.py
```

The script upserts a briefing (`upsert_for_assistant`), retrieves it (`retrieve_for_assistant`), then deletes the attachment (`delete_for_assistant`). Async variants: `*_async` on the same methods.

## Methods

??? example "`unique_sdk.Briefing.retrieve_for_assistant` - Retrieve briefing for an assistant"

    Returns the briefing attached to the assistant identified by `assistant_id` (`GET /briefings/{assistantId}`).

    **Parameters:**

    - `user_id` (str, required)
    - `company_id` (str, required)
    - `assistant_id` (str, required) — Max length **128** on the API.

    **Returns:** A [`Briefing`](#briefing) instance (`200`).

    **Example:**

    ```python
    briefing = unique_sdk.Briefing.retrieve_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_id,
    )
    print(briefing["text"])
    ```

??? example "`unique_sdk.Briefing.retrieve_for_assistant_async` - Async retrieve"

    Same as **`retrieve_for_assistant`**, but asynchronous.

??? example "`unique_sdk.Briefing.upsert_for_assistant` - Upsert briefing for an assistant"

    Create or update the briefing for the assistant identified by `assistant_id` (`PUT /briefings/{assistantId}`) with a JSON body matching OpenAPI `PublicUpsertBriefingRequestDto`:

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

??? example "`unique_sdk.Briefing.delete_for_assistant` - Delete briefing attachment for an assistant"

    Detaches the briefing from the assistant (`DELETE /briefings/{assistantId}`). The underlying briefing record is preserved when other assistants in the tenant still reference it.

    **Returns:** A [`DeletedObject`](#deletedobject) (`200`).

    **Example:**

    ```python
    result = unique_sdk.Briefing.delete_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_id,
    )
    assert result["deleted"] is True
    ```

??? example "`unique_sdk.Briefing.delete_for_assistant_async` - Async delete"

    Same as **`delete_for_assistant`**, but asynchronous.

## Input and return types

#### UpsertForAssistantParams {#upsertforassistantparams}

??? note "Request body (`PublicUpsertBriefingRequestDto`)"

    - `text`, `generatedAt`, `prompts` — Required on the wire (see upsert method above).
    - `title` — Optional display title (max **100**).
    - `markdown` / `content` — Legacy aliases mapped to **`text`**.

    Per-call `api_key`, `api_base`, and `headers` are transport-only and not sent in the JSON body.

#### Briefing {#briefing}

??? note "The `Briefing` resource object (`PublicBriefingDto`)"

    - `object` — `"briefing"`
    - `externalId` — Stable external identifier (assistant id when attached per-assistant)
    - `text`, `generatedAt`, `title`, `createdAt`, `updatedAt`
    - `prompts` — Ordered prompt rows when returned

    Legacy fields such as `assistantId` or `id` may still appear depending on API version.

    **Returned by:** `retrieve_for_assistant()`, `upsert_for_assistant()` (+ async variants)

#### DeletedObject {#deletedobject}

??? note "Delete response"

    - `object` — `"deleted-briefing"`
    - `id` — Echoes the `assistantId` from the URL
    - `deleted` — Whether the detach succeeded

    **Returned by:** `delete_for_assistant()` (+ async variant)

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
