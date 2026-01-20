# Elicitation API

The Elicitation API allows you to create and manage user interaction requests in Unique AI (compatible with release > 2026.04).

## Overview

Elicitations are requests for user input that can be displayed as forms or external URLs. Use this API to:

- Create elicitation requests for user input
- Get pending elicitations for a user
- Retrieve specific elicitation details
- Respond to elicitation requests

## Methods

??? example "`unique_sdk.Elicitation.create_elicitation` - Create an elicitation request"

    Create an elicitation request to gather user input.

    **Parameters:**

    - `mode` (Literal["FORM", "URL"], required) - The elicitation mode
        - `"FORM"` - Display a form based on the schema
        - `"URL"` - Redirect to an external URL
    - `message` (str, required) - The message to display to the user
    - `toolName` (str, required) - The name of the tool requesting the elicitation
    - `schema` (Dict, optional) - JSON schema for form mode (required when mode is "FORM")
    - `url` (str, optional) - External URL for URL mode (required when mode is "URL")
    - `externalElicitationId` (str, optional) - External identifier for the elicitation
    - `chatId` (str, optional) - Associated chat ID
    - `messageId` (str, optional) - Associated message ID
    - `expiresInSeconds` (int, optional) - Expiration time in seconds
    - `metadata` (Dict, optional) - Additional metadata

    **Returns:**

    Returns an [`Elicitation`](#elicitation) object.

    **Example - Form Mode:**

    ```python
    elicitation = unique_sdk.Elicitation.create_elicitation(
        user_id=user_id,
        company_id=company_id,
        mode="FORM",
        message="Please provide your feedback",
        toolName="feedback_collector",
        schema={
            "type": "object",
            "properties": {
                "rating": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Rating from 1-5"
                },
                "comment": {
                    "type": "string",
                    "description": "Your feedback"
                }
            },
            "required": ["rating"]
        },
        expiresInSeconds=3600,
    )
    print(f"Created elicitation: {elicitation['id']}")
    ```

    **Example - URL Mode:**

    ```python
    elicitation = unique_sdk.Elicitation.create_elicitation(
        user_id=user_id,
        company_id=company_id,
        mode="URL",
        message="Please complete the survey",
        toolName="survey_tool",
        url="https://example.com/survey?id=123",
        externalElicitationId="survey_123",
    )
    ```

??? example "`unique_sdk.Elicitation.get_pending_elicitations` - Get pending elicitations"

    Get all pending elicitation requests for a user.

    **Returns:**

    Returns an [`Elicitations`](#elicitations) object.

    **Example:**

    ```python
    pending = unique_sdk.Elicitation.get_pending_elicitations(
        user_id=user_id,
        company_id=company_id,
    )
    
    for elicitation in pending['elicitations']:
        print(f"Pending: {elicitation['id']} - {elicitation['message']}")
    ```

??? example "`unique_sdk.Elicitation.get_elicitation` - Get elicitation by ID"

    Get a specific elicitation request by its ID.

    **Parameters:**

    - `elicitation_id` (str, required) - The ID of the elicitation to retrieve

    **Returns:**

    Returns an [`Elicitation`](#elicitation) object.

    **Example:**

    ```python
    elicitation = unique_sdk.Elicitation.get_elicitation(
        user_id=user_id,
        company_id=company_id,
        elicitation_id="elicit_abc123",
    )
    
    print(f"Status: {elicitation['status']}")
    print(f"Message: {elicitation['message']}")
    ```

??? example "`unique_sdk.Elicitation.respond_to_elicitation` - Respond to an elicitation"

    Submit a response to an elicitation request.

    **Parameters:**

    - `elicitationId` (str, required) - The ID of the elicitation to respond to
    - `action` (Literal["ACCEPT", "DECLINE", "CANCEL"], required) - The response action
        - `"ACCEPT"` - Accept and provide content
        - `"DECLINE"` - Decline the request
        - `"CANCEL"` - Cancel the elicitation
    - `content` (Dict, optional) - The response content (required when action is "ACCEPT")

    **Returns:**

    Returns an [`ElicitationResponseResult`](#elicitationresponseresult) object.

    **Example - Accept with Content:**

    ```python
    result = unique_sdk.Elicitation.respond_to_elicitation(
        user_id=user_id,
        company_id=company_id,
        elicitationId="elicit_abc123",
        action="ACCEPT",
        content={
            "rating": 5,
            "comment": "Great experience!"
        }
    )
    
    if result['success']:
        print("Response submitted successfully")
    ```

    **Example - Decline:**

    ```python
    result = unique_sdk.Elicitation.respond_to_elicitation(
        user_id=user_id,
        company_id=company_id,
        elicitationId="elicit_abc123",
        action="DECLINE",
    )
    ```

## Return Types

#### Elicitation {#elicitation}

??? note "The `Elicitation` object represents an elicitation request"

    **Fields:**

    - `id` (str) - Unique elicitation identifier
    - `object` (str) - Object type
    - `source` (str) - Source of the elicitation
    - `mode` (str) - Elicitation mode ("FORM" or "URL")
    - `status` (str) - Current status of the elicitation
    - `message` (str) - Message displayed to the user
    - `mcpServerId` (str, optional) - MCP server ID if applicable
    - `toolName` (str, optional) - Name of the requesting tool
    - `schema` (Dict, optional) - JSON schema for form mode
    - `url` (str, optional) - External URL for URL mode
    - `externalElicitationId` (str, optional) - External identifier
    - `responseContent` (Dict, optional) - User's response content
    - `respondedAt` (str, optional) - Response timestamp (ISO 8601)
    - `companyId` (str) - Company identifier
    - `userId` (str) - User identifier
    - `chatId` (str, optional) - Associated chat ID
    - `messageId` (str, optional) - Associated message ID
    - `metadata` (Dict, optional) - Additional metadata
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str, optional) - Last update timestamp (ISO 8601)
    - `expiresAt` (str, optional) - Expiration timestamp (ISO 8601)

    **Returned by:** `create_elicitation()`, `get_elicitation()`

#### Elicitations {#elicitations}

??? note "The `Elicitations` object contains a list of elicitations"

    **Fields:**

    - `elicitations` (List[Elicitation]) - List of elicitation objects. See [`Elicitation`](#elicitation) for properties.

    **Returned by:** `get_pending_elicitations()`

#### ElicitationResponseResult {#elicitationresponseresult}

??? note "The `ElicitationResponseResult` object represents the result of responding to an elicitation"

    **Fields:**

    - `success` (bool) - Whether the response was successful
    - `message` (str, optional) - Additional message or error details

    **Returned by:** `respond_to_elicitation()`

## Related Resources

- [Message API](message.md) - Manage chat messages
- [Space API](space.md) - Manage conversational spaces

