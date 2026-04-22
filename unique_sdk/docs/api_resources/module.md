# Module API

Create, list, retrieve, update, and delete assistant modules. Modules define the behaviour, tools, and instructions attached to an assistant (space).

## Overview

Each module belongs to an **assistant** and configures:

- A **name** and optional **description**
- A **weight** controlling evaluation priority (higher = higher priority)
- Whether the module is **external** (`isExternal`)
- Whether **custom instructions** are enabled (`isCustomInstructionEnabled`)
- An optional **configuration** object (arbitrary key/value settings)
- An optional **tool definition** object (tool-specific schema)
- An optional **moduleTemplateId** linking the module to a predefined template

## Methods

??? example "`unique_sdk.Module.list` - List modules"

    List all modules accessible to the authenticated user, optionally filtered by assistant.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `assistantId` (str, optional) - Filter modules belonging to this assistant ID

    **Returns:**

    Returns a list of [`Module`](#module) objects.

    **Example - List all modules:**

    ```python
    modules = unique_sdk.Module.list(
        user_id="user_123",
        company_id="company_456",
    )
    for module in modules:
        print(f"{module.id}: {module.name} (weight={module.weight})")
    ```

    **Example - Filter by assistant:**

    ```python
    modules = unique_sdk.Module.list(
        user_id="user_123",
        company_id="company_456",
        assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
    )
    ```

??? example "`unique_sdk.Module.retrieve` - Get a module by ID"

    Retrieve full details of a single module.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `id` (str, required) - The module identifier

    **Returns:**

    Returns a [`Module`](#module) object.

    **Example:**

    ```python
    module = unique_sdk.Module.retrieve(
        user_id="user_123",
        company_id="company_456",
        id="module_u3x61phmqxvlhswjlm3byvvr",
    )
    print(f"Name: {module.name}")
    print(f"Assistant: {module.assistantId}")
    print(f"Weight: {module.weight}")
    print(f"External: {module.isExternal}")
    ```

??? example "`unique_sdk.Module.create` - Create a module"

    Create a new module and attach it to an assistant.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `assistantId` (str, required) - ID of the assistant this module belongs to
    - `name` (str, required) - Module name
    - `description` (str, optional) - Human-readable description
    - `weight` (int, optional) - Priority weight (higher = higher priority, e.g. `10000`)
    - `isExternal` (bool, optional) - Whether the module is external. Defaults to `False`.
    - `isCustomInstructionEnabled` (bool, optional) - Whether custom instructions are enabled. Defaults to `False`.
    - `configuration` (dict, optional) - Arbitrary configuration key/value pairs
    - `toolDefinition` (dict, optional) - Tool definition schema
    - `moduleTemplateId` (str, optional) - ID of a module template to base this module on

    **Returns:**

    Returns the created [`Module`](#module) object.

    **Example - Minimal:**

    ```python
    module = unique_sdk.Module.create(
        user_id="user_123",
        company_id="company_456",
        assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
        name="UniqueAi",
    )
    print(f"Created: {module.id}")
    ```

    **Example - With configuration:**

    ```python
    module = unique_sdk.Module.create(
        user_id="user_123",
        company_id="company_456",
        assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
        name="SearchModule",
        description="Provides vector search capabilities",
        weight=10000,
        isCustomInstructionEnabled=True,
        configuration={"maxResults": 10, "threshold": 0.7},
    )
    ```

    **Example - From a template:**

    ```python
    module = unique_sdk.Module.create(
        user_id="user_123",
        company_id="company_456",
        assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
        name="AnalyticsModule",
        moduleTemplateId="moduletemplate_abc123",
    )
    ```

??? example "`unique_sdk.Module.modify` - Update a module"

    Update an existing module.  Only the fields you supply are changed; everything else remains unchanged.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `id` (str, required) - The module identifier
    - `name` (str, optional) - Updated name
    - `description` (str | None, optional) - Updated description. Pass `None` to clear.
    - `weight` (int, optional) - Updated priority weight
    - `isExternal` (bool, optional) - Update external flag
    - `isCustomInstructionEnabled` (bool, optional) - Update custom instruction flag
    - `configuration` (dict, optional) - Updated configuration object
    - `toolDefinition` (dict, optional) - Updated tool definition

    **Returns:**

    Returns the updated [`Module`](#module) object.

    **Example - Rename and change weight:**

    ```python
    module = unique_sdk.Module.modify(
        user_id="user_123",
        company_id="company_456",
        id="module_u3x61phmqxvlhswjlm3byvvr",
        name="RenamedModule",
        weight=5000,
    )
    ```

    **Example - Update configuration:**

    ```python
    module = unique_sdk.Module.modify(
        user_id="user_123",
        company_id="company_456",
        id="module_u3x61phmqxvlhswjlm3byvvr",
        configuration={"maxResults": 20, "threshold": 0.8},
    )
    ```

    **Example - Enable custom instructions:**

    ```python
    module = unique_sdk.Module.modify(
        user_id="user_123",
        company_id="company_456",
        id="module_u3x61phmqxvlhswjlm3byvvr",
        isCustomInstructionEnabled=True,
    )
    ```

??? example "`unique_sdk.Module.delete` - Delete a module"

    Permanently delete a module.  This action cannot be undone.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `id` (str, required) - The module identifier

    **Returns:**

    Returns a `DeletedObject` dict with `id`, `object`, and `deleted` fields.

    **Example:**

    ```python
    result = unique_sdk.Module.delete(
        user_id="user_123",
        company_id="company_456",
        id="module_u3x61phmqxvlhswjlm3byvvr",
    )
    if result["deleted"]:
        print(f"Deleted module {result['id']}")
    ```

## Async Methods

All methods have async variants with an `_async` suffix:

- `list_async`
- `retrieve_async`
- `create_async`
- `modify_async`
- `delete_async`

```python
module = await unique_sdk.Module.create_async(
    user_id="user_123",
    company_id="company_456",
    assistantId="assistant_cvj3fd7x8hpt1hfp0akqu1rq",
    name="AsyncModule",
    weight=10000,
)
```

## Return Types

#### Module {#module}

??? note "The `Module` object represents an assistant module"

    **Fields:**

    - `id` (str) - Unique module identifier
    - `name` (str) - Module name
    - `description` (str | None) - Human-readable description
    - `toolDefinition` (dict | None) - Tool definition schema
    - `configuration` (dict | None) - Arbitrary configuration key/value pairs
    - `assistantId` (str) - ID of the assistant this module belongs to
    - `weight` (int | None) - Priority weight (higher = higher priority)
    - `isExternal` (bool) - Whether the module is external
    - `isCustomInstructionEnabled` (bool) - Whether custom instructions are enabled
    - `moduleTemplateId` (str | None) - ID of the module template, if any
    - `createdAt` (str) - ISO 8601 creation timestamp
    - `updatedAt` (str) - ISO 8601 last update timestamp

    **Returned by:** `list()`, `retrieve()`, `create()`, `modify()`

#### DeletedObject

??? note "Returned by `delete()`"

    - `id` (str) - ID of the deleted module
    - `object` (str) - Always `"deleted-module"`
    - `deleted` (bool) - Always `True` on success

## Related Resources

- [Space API](space.md) - Manage assistants (spaces) and their associated modules
- [Scheduled Task API](scheduled_task.md) - Trigger assistants on a cron schedule
