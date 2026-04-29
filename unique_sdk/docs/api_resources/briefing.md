# Briefing API

The Briefing API creates or replaces the briefing attached to an assistant using the assistant’s identifier. The API upserts the briefing with that id as its external id (see `PUT /briefings/{assistantId}` in the public OpenAPI specification).

## Overview

Use this API when you need to:

- Attach or update long-form briefing text for a specific assistant (space)
- Keep assistant context in sync from automation or admin tools

Callers must have permission to manage the target assistant; the server returns `403` when access is denied and `404` when the assistant does not exist.

## Methods

??? example "`unique_sdk.Briefing.upsert_for_assistant` - Upsert briefing for an assistant"

    Create or update the briefing for the assistant identified by `assistant_id`. The HTTP request is `PUT /briefings/{assistantId}` with a JSON body matching OpenAPI `UpsertBriefingRequest`.

    **Parameters:**

    - `user_id` (str, required) - Authenticated user id (forwarded via `x-user-id`).
    - `company_id` (str, required) - Company scope (forwarded via `x-company-id`).
    - `assistant_id` (str, required) - Identifier of the assistant the briefing belongs to (path segment; URI-encoded when necessary). Matches OpenAPI path `assistantId` (max length 128 in the schema).
    - `content` (str, required) - Briefing body text. Mirrors the `UpsertBriefingRequest` field in the SDK; extend typed fields in [`UpsertForAssistantParams`](#upsertforassistantparams) when the stable OpenAPI gains additional keys.

    **Returns:**

    Returns a [`Briefing`](#briefing) instance (`200`).

    **Example:**

    ```python
    briefing = unique_sdk.Briefing.upsert_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_external_id,
        content="# Role\nAssist users with onboarding...",
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
        content="Updated briefing text.",
    )
    ```

## Input and return types

#### UpsertForAssistantParams {#upsertforassistantparams}

??? note "Request body (`UpsertBriefingRequest`)"

    The SDK exposes this as typed keyword arguments unpacked into the JSON body.

    **Fields:**

    - `content` (str, required) - Briefing content to store.

    Optional per-call overrides (such as `api_key`, `api_base`, or extra `headers`) follow the usual SDK patterns; see [Configuration](../getting_started/configuration.md) for global defaults.

#### Briefing {#briefing}

??? note "The `Briefing` resource object"

    **Typical fields (from the public `Briefing` schema):**

    - `id` (str) - Briefing identifier
    - `object` (str) - Always `"briefing"` for typed SDK responses
    - `assistantId` (str) - Assistant this briefing is attached to
    - `content` (str, optional) - Stored briefing text, if present on the response
    - `title` (str, optional) - Title if exposed by the API
    - `createdAt` (str, optional) - Creation timestamp (ISO 8601)
    - `updatedAt` (str, optional) - Last update timestamp (ISO 8601)

    **Returned by:** `upsert_for_assistant()`, `upsert_for_assistant_async()`

## HTTP status semantics

The underlying route can return:

- `200` — Briefing created or updated and attached to the assistant.
- `400` — Invalid request parameters.
- `401` — Missing or invalid authentication.
- `403` — Caller lacks manage access to the assistant.
- `404` — Assistant not found.
- `422` — Request could not be processed due to an upstream service error.

## Related resources

- [Space API](space.md) — Create and configure assistants (spaces)
