# Project Memory API

The Project Memory API reads, writes and deletes the memory of a project, for the project's owner. It is service-only: the project memory service calls it and identifies itself with `service_id`.

## Overview

A project groups a user's chats in a space. Each project has one project memory, built from the user's project chats by a nightly data science job and read into every chat of the project.

Access:

- **Service-only.** Only the project memory service (`service_id="assistants-core"`) may call the endpoint. It acts for the project's owner, so every call also takes the owner's `user_id` and `company_id`. The SDK sends `service_id` as the `x-service-id` header. Calls without it, including direct calls by the owner, get `403 Forbidden` (`PermissionError`).
- **Owner scope.** A project that does not exist, or belongs to another user or company, gets `404 Not Found` (`InvalidRequestError`).
- **Projects flag.** The Projects feature flag must be enabled for the owner; otherwise every call gets `403 Forbidden`.

A project memory holds:

- `document` - markdown that project chats read, at most 32 KB of UTF-8
- `state` - opaque JSON owned by the project memory job, at most 256 KB of UTF-8. Not meant for display.

Until the memory is first written, `id`, `document`, `state`, `createdAt` and `updatedAt` are `None`. Deleting the project also deletes its memory.

## Methods

??? example "`unique_sdk.ProjectMemory.retrieve` - Retrieve project memory"

    Retrieve the memory of a project, for its owner.

    **Parameters:**

    - `user_id` (str, required) - The project owner's user identifier
    - `company_id` (str, required) - The owner's company identifier
    - `project_id` (str, required) - Project identifier
    - `service_id` (str, keyword-only) - The calling service, sent as `x-service-id`. Required by the endpoint: `"assistants-core"`.

    **Returns:**

    Returns a [`ProjectMemory`](#projectmemory) object. Its fields are `None` until the memory is first written.

    **Example:**

    ```python
    memory = unique_sdk.ProjectMemory.retrieve(
        user_id=owner_id,
        company_id=company_id,
        project_id=project_id,
        service_id="assistants-core",
    )

    if memory.document is None:
        print("No project memory yet")
    ```

??? example "`unique_sdk.ProjectMemory.modify` - Create or replace project memory"

    Create or replace the memory of a project, for its owner.

    **Parameters:**

    - `user_id` (str, required) - The project owner's user identifier
    - `company_id` (str, required) - The owner's company identifier
    - `project_id` (str, required) - Project identifier
    - `document` (str, required) - Markdown document that replaces the stored one
    - `state` (str, optional) - JSON string that replaces the stored job state. When omitted, the stored state is kept.
    - `service_id` (str, keyword-only) - The calling service, sent as `x-service-id`. Required by the endpoint: `"assistants-core"`.

    **Returns:**

    Returns the updated [`ProjectMemory`](#projectmemory) object.

    **Example - Update the document only:**

    ```python
    memory = unique_sdk.ProjectMemory.modify(
        user_id=owner_id,
        company_id=company_id,
        project_id=project_id,
        document="# Project memory\n\n## Goals and scope\n- **Goal:** ...",
        service_id="assistants-core",
    )
    ```

    **Example - Update document and job state together:**

    ```python
    memory = unique_sdk.ProjectMemory.modify(
        user_id=owner_id,
        company_id=company_id,
        project_id=project_id,
        document=rendered_markdown,
        state=json.dumps(job_state),
        service_id="assistants-core",
    )
    ```

??? example "`unique_sdk.ProjectMemory.delete` - Delete project memory"

    Delete the memory of a project, for its owner. Deleting a memory that does not exist succeeds.

    **Parameters:**

    - `user_id` (str, required) - The project owner's user identifier
    - `company_id` (str, required) - The owner's company identifier
    - `project_id` (str, required) - Project identifier
    - `service_id` (str, keyword-only) - The calling service, sent as `x-service-id`. Required by the endpoint: `"assistants-core"`.

    **Returns:**

    Returns a deleted object: `id` (the project id), `object` (`"project-memory"`) and `deleted` (`True`).

    **Example:**

    ```python
    unique_sdk.ProjectMemory.delete(
        user_id=owner_id,
        company_id=company_id,
        project_id=project_id,
        service_id="assistants-core",
    )
    ```

## Async Methods

All methods have async variants with an `_async` suffix, with the same parameters:

- `retrieve_async`
- `modify_async`
- `delete_async`

```python
memory = await unique_sdk.ProjectMemory.retrieve_async(
    user_id=owner_id,
    company_id=company_id,
    project_id=project_id,
    service_id="assistants-core",
)
```

## Return Types

#### ProjectMemory {#projectmemory}

??? note "The `ProjectMemory` object represents the memory of one project"

    **Fields:**

    - `id` (str | None) - Memory identifier; `None` until first written
    - `projectId` (str) - Project identifier
    - `document` (str | None) - Markdown memory document; `None` until first written
    - `state` (str | None) - Opaque JSON state of the project memory job; `None` until the job first writes it
    - `createdAt` (str | None) - Creation timestamp in ISO 8601 format
    - `updatedAt` (str | None) - Last update timestamp in ISO 8601 format
    - `object` (Literal["project-memory"]) - Object type identifier

    **Returned by:** `ProjectMemory.retrieve()`, `ProjectMemory.modify()`

## Related Resources

- [Context Memory API](context_memory.md) - Persistent user context memory
- [Space API](space.md) - Spaces, which projects belong to
