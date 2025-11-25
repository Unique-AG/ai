# Message Assessment API

The Message Assessment API evaluates assistant messages for quality, hallucinations, and compliance.

## Overview

Create assessments to track:

- Hallucination detection
- Compliance violations
- Response quality
- Factual accuracy

## Methods

??? example "`unique_sdk.MessageAssessment.create` - Create assessment"

    Create a new assessment for an assistant message.

    **Parameters:**

    - `messageId` (str, required) - Message ID to assess
    - `status` (Literal["PENDING", "DONE", "ERROR"], required) - Assessment status
    - `type` (Literal["HALLUCINATION", "COMPLIANCE"], required) - Assessment type
    - `isVisible` (bool, required) - Whether to show assessment to user
    - `title` (str | None, optional) - Assessment title
    - `explanation` (str | None, optional) - Detailed explanation
    - `label` (Literal["RED", "YELLOW", "GREEN"] | None, optional) - Color label

    **Returns:**

    Returns a [`MessageAssessment`](#messageassessment) object.

    **Example:**

    ```python
    assessment = unique_sdk.MessageAssessment.create(
        user_id=user_id,
        company_id=company_id,
        assistant_message_id="msg_abc123",
        status="DONE",
        label="RED",
        type="HALLUCINATION",
        title="Hallucination detected",
        explanation="The response contains information not found in source documents.",
        isVisible=True
    )
    ```

??? example "`unique_sdk.MessageAssessment.modify` - Update assessment"

    Update an existing assessment.

    **Parameters:**

    - `messageId` (str, required) - Message ID of the assessment to update
    - `type` (Literal["HALLUCINATION", "COMPLIANCE"], required) - Assessment type
    - `status` (Literal["PENDING", "DONE", "ERROR"] | None, optional) - Updated status
    - `title` (str | None, optional) - Updated title
    - `explanation` (str | None, optional) - Updated explanation
    - `label` (Literal["RED", "YELLOW", "GREEN"] | None, optional) - Updated label

    **Returns:**

    Returns a [`MessageAssessment`](#messageassessment) object.

    **Example:**

    ```python
    assessment = unique_sdk.MessageAssessment.modify(
        user_id=user_id,
        company_id=company_id,
        assistant_message_id="msg_abc123",
        status="DONE",
        label="YELLOW",
        type="HALLUCINATION",
        title="Minor inconsistency found",
        explanation="Updated assessment after review."
    )
    ```

## Use Cases

??? example "Hallucination Detection"

    ```python
    def detect_hallucination(assistant_message_id, response_text, source_documents):
        """Check for hallucinations in assistant response."""
        
        # Analyze response against sources
        has_hallucination, details = check_against_sources(
            response_text,
            source_documents
        )
        
        if has_hallucination:
            # Create assessment
            unique_sdk.MessageAssessment.create(
                user_id=user_id,
                company_id=company_id,
                messageId=assistant_message_id,
                status="DONE",
                label="RED",
                type="HALLUCINATION",
                title="Hallucination Detected",
                explanation=f"Found unsupported claims: {details}",
                isVisible=True
            )
        else:
            # Create positive assessment
            unique_sdk.MessageAssessment.create(
                user_id=user_id,
                company_id=company_id,
                messageId=assistant_message_id,
                status="DONE",
                label="GREEN",
                type="HALLUCINATION",
                title="No Hallucinations",
                explanation="All claims are supported by source documents.",
                isVisible=False  # Don't show positive checks to user
            )
    ```

??? example "Compliance Checking"

    ```python
    def check_compliance(assistant_message_id, response_text):
        """Check response for compliance violations."""
        
        violations = []
        
        # Check for PII
        if contains_pii(response_text):
            violations.append("Contains Personal Identifiable Information")
        
        # Check for prohibited content
        if contains_prohibited_content(response_text):
            violations.append("Contains prohibited content")
        
        # Check for policy violations
        if violates_policy(response_text):
            violations.append("Violates company policy")
        
        if violations:
            unique_sdk.MessageAssessment.create(
                user_id=user_id,
                company_id=company_id,
                messageId=assistant_message_id,
                status="DONE",
                label="RED",
                type="COMPLIANCE",
                title="Compliance Violations",
                explanation="; ".join(violations),
                isVisible=True
            )
            return False
        
        return True
    ```

## Best Practices

??? example "Clear Explanations"

    ```python
    # Good: Specific and actionable
    unique_sdk.MessageAssessment.create(
        ...
        title="Unsupported Claim Detected",
        explanation="The response states 'revenue increased by 40%' but source document shows 30%. See paragraph 3 in Q4_Report.pdf"
    )

    # Bad: Vague
    unique_sdk.MessageAssessment.create(
        ...
        title="Error",
        explanation="Something is wrong"
    )
    ```

??? example "Appropriate Visibility"

    ```python
    # Show critical issues to users
    unique_sdk.MessageAssessment.create(
        label="RED",
        isVisible=True,  # User should see this
        ...
    )

    # Hide positive checks
    unique_sdk.MessageAssessment.create(
        label="GREEN",
        isVisible=False,  # No need to show passing checks
        ...
    )
    ```

??? example "Consistent Labeling"

    ```python
    # Define constants for consistency
    class AssessmentLabel:
        CRITICAL = "RED"      # Serious issues
        WARNING = "YELLOW"    # Minor concerns
        PASSED = "GREEN"      # No issues

    # Use consistently
    unique_sdk.MessageAssessment.create(
        label=AssessmentLabel.CRITICAL,
        ...
    )
    ```

## Return Types

#### MessageAssessment {#messageassessment}

??? note "The `MessageAssessment` object represents an assessment of a message"

    **Fields:**

    - `id` (str) - Unique assessment identifier
    - `messageId` (str) - Associated message ID
    - `status` (Literal["PENDING", "DONE", "ERROR"]) - Assessment status
    - `type` (Literal["HALLUCINATION", "COMPLIANCE"]) - Assessment type
    - `isVisible` (bool) - Whether assessment is visible to user
    - `title` (str | None) - Assessment title
    - `explanation` (str | None) - Detailed explanation
    - `label` (Literal["RED", "YELLOW", "GREEN"] | None) - Color label
    - `createdAt` (str | None) - Creation timestamp (ISO 8601)
    - `updatedAt` (str | None) - Last update timestamp (ISO 8601)

    **Returned by:** `MessageAssessment.create()`, `MessageAssessment.modify()`

## Related Resources

- [Message API](message.md) - Manage messages
- [Message Log API](message_log.md) - Track assessment process
- [Message Execution API](message_execution.md) - Track long-running assessments

