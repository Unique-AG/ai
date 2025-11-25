# Message Log API

The Message Log API updates the steps section of messages in the chat UI during execution.

## Overview

Create and update log entries to show execution progress in the chat interface. Useful for displaying:

- Processing steps
- Status updates
- References and details
- Operation progress

## Methods

??? example "`unique_sdk.MessageLog.create` - Create log entry"

    Create a new log entry for a message.

    **Parameters:**

    - `messageId` (str, required) - Message ID to log for
    - `text` (str, required) - Log entry text
    - `order` (int, required) - Display order
    - `status` (Literal["RUNNING", "COMPLETED", "FAILED"], required) - Log entry status
    - `details` (Dict[str, Any] | None, optional) - Additional details dictionary
    - `uncitedReferences` (Dict[str, Any] | None, optional) - Uncited references dictionary
    - `references` (List[Reference] | None, optional) - List of references. See [`MessageLog.Reference`](#messagelogreference) for structure.

    **Returns:**

    Returns a [`MessageLog`](#messagelog) object.

    **Example:**

    ```python
    log = unique_sdk.MessageLog.create(
        user_id=user_id,
        company_id=company_id,
        messageId="msg_a0jgnt1jrqv1d3uzr450waxw",
        text="Searching knowledge base...",
        order=1,
        status="RUNNING"
    )
    ```

??? example "`unique_sdk.MessageLog.update` - Update log entry"

    Update an existing log entry.

    **Parameters:**

    - `message_log_id` (str, required) - Message log ID to update
    - `text` (str | None, optional) - Updated log entry text
    - `status` (Literal["RUNNING", "COMPLETED", "FAILED"] | None, optional) - Updated status
    - `order` (int | None, optional) - Updated display order
    - `details` (Dict[str, Any] | None, optional) - Updated details dictionary
    - `uncitedReferences` (Dict[str, Any] | None, optional) - Updated uncited references
    - `references` (List[Reference] | None, optional) - Updated references. See [`MessageLog.Reference`](#messagelogreference) for structure.

    **Returns:**

    Returns a [`MessageLog`](#messagelog) object.

    **Example:**

    ```python
    log = unique_sdk.MessageLog.update(
        user_id=user_id,
        company_id=company_id,
        message_log_id="message_log_fd7z7gjljo1z2wu5g6l9q7r9",
        text="Search completed",
        status="COMPLETED",
        details={"results_found": 42}
    )
    ```

## Input Types

#### MessageLog.Reference {#messagelogreference}

??? note "The `MessageLog.Reference` type defines source reference information for log entries"

    **Fields:**

    - `name` (str) - Reference name/title
    - `description` (str | None) - Reference description
    - `url` (str | None) - Reference URL
    - `sequenceNumber` (int) - Sequence number for ordering references
    - `originalIndex` (list[int] | None) - Original index positions
    - `sourceId` (str) - Source identifier
    - `source` (str) - Source name/path

    **Used in:** `MessageLog.create()`, `MessageLog.update()`

## Return Types

#### MessageLog {#messagelog}

??? note "The `MessageLog` object represents a log entry for a message"

    **Fields:**

    - `id` (str) - Unique log entry identifier
    - `messageId` (str) - Associated message ID
    - `status` (Literal["RUNNING", "COMPLETED", "FAILED"]) - Log entry status
    - `text` (str) - Log entry text
    - `details` (Dict[str, Any]) - Additional details dictionary
    - `uncitedReferences` (Dict[str, Any]) - Uncited references dictionary
    - `order` (int) - Display order
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)
    - `references` (List[Reference] | None) - List of references. See [`MessageLog.Reference`](#messagelogreference) for structure.

    **Returned by:** `MessageLog.create()`, `MessageLog.update()`

## Related Resources

- [Message API](message.md) - Create and manage messages
- [Message Execution API](message_execution.md) - Track long-running operations
- [Message Assessment API](message_assessment.md) - Evaluate message quality

