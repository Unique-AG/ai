# Message Execution API

The Message Execution API tracks and manages long-running message operations.

## Overview

Track execution progress for operations like:

- Deep research
- Complex analysis
- Multi-step workflows
- Long-running tasks

## Methods

??? example "`unique_sdk.MessageExecution.create` - Create execution tracker"

    Create a message execution tracker.

    **Parameters:**

    - `messageId` (str, required) - Message ID to track
    - `type` (Literal["DEEP_RESEARCH"], required) - Execution type

    **Returns:**

    Returns a [`MessageExecution`](#messageexecution) object.

    **Example:**

    ```python
    execution = unique_sdk.MessageExecution.create(
        user_id=user_id,
        company_id=company_id,
        messageId="msg_a0jgnt1jrqv143uzr750waxw",
        type="DEEP_RESEARCH"
    )
    ```

??? example "`unique_sdk.MessageExecution.get` - Get execution status"

    Get the current execution status for a message.

    **Parameters:**

    - `messageId` (str, required) - Message ID to get execution status for

    **Returns:**

    Returns a [`MessageExecution`](#messageexecution) object.

    **Example:**

    ```python
    execution = unique_sdk.MessageExecution.get(
        user_id=user_id,
        company_id=company_id,
        messageId="msg_a0jgnt1jrqv143uzr750waxw"
    )
    ```

??? example "`unique_sdk.MessageExecution.update` - Update execution progress"

    Update execution progress and status.

    **Parameters:**

    - `messageId` (str, required) - Message ID to update execution for
    - `status` (Literal["COMPLETED", "FAILED"] | None, optional) - Execution status
    - `secondsRemaining` (int | None, optional) - Estimated seconds remaining
    - `percentageCompleted` (int | None, optional) - Progress percentage (0-100)

    **Returns:**

    Returns a [`MessageExecution`](#messageexecution) object.

    **Example:**

    ```python
    unique_sdk.MessageExecution.update(
        user_id=user_id,
        company_id=company_id,
        messageId="msg_a0jgnt1jrqv143uzr750waxw",
        status="COMPLETED",
        percentageCompleted=100
    )
    ```

## Return Types

#### MessageExecution {#messageexecution}

??? note "The `MessageExecution` object represents execution tracking for a message"

    **Fields:**

    - `id` (str) - Unique execution identifier
    - `messageId` (str) - Associated message ID
    - `status` (Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]) - Execution status
    - `type` (Literal["DEEP_RESEARCH"]) - Execution type
    - `secondsRemaining` (int | None) - Estimated seconds remaining
    - `percentageCompleted` (int | None) - Progress percentage (0-100)
    - `positionInQueue` (int | None) - Position in execution queue
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)

    **Returned by:** `MessageExecution.create()`, `MessageExecution.get()`, `MessageExecution.update()`

## Related Resources

- [Message API](message.md) - Create and manage messages
- [Message Log API](message_log.md) - Track execution steps
- [Message Assessment API](message_assessment.md) - Evaluate results

