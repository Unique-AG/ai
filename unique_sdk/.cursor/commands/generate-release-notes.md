---
description: Generate release notes for SDK changes
---

# Generate SDK Release Notes

When asked to generate release notes, create documentation in this format:

## Format

```
SDK
What's New

<emoji> <Feature Title> - <Brief description of what it does and when to use it.>

Example

```python
<code example showing basic usage>
```
```

## Instructions

1. **Read the CHANGELOG.md** to see what was added in the latest version
2. **Read the relevant SDK file** to understand the feature
3. **Generate user-friendly release notes** with:
   - Clear feature title
   - Brief description of what it does
   - When/why to use it
   - Working code example

## Template

```
SDK
What's New

<emoji> <Feature Title> - <Description>. <Optional: when to use it or key benefit>.

Example

```python
result = unique_sdk.Resource.method(
    user_id=user_id,
    company_id=company_id,
    param="value",  # Comment explaining the param
)
```
```

## Examples

### New Method Example
```
SDK
What's New

Update Ingestion State - Re-queue content for ingestion or mark it with a specific state. Useful for re-processing failed content.

Example

```python
unique_sdk.Content.update_ingestion_state(
    user_id=user_id,
    company_id=company_id,
    contentId="cont_abc123",
    ingestionState="Queued",  # Options: Queued, Processing, Completed, Failed, Pending
)
```
```

### New Parameter Example
```
SDK
What's New

Message Correlation - Link messages to parent messages in other chats. Useful for tracking conversation threads across spaces.

Example

```python
message = unique_sdk.Message.create(
    user_id=user_id,
    company_id=company_id,
    chatId=chat_id,
    assistantId=assistant_id,
    text="Follow-up message",
    role="ASSISTANT",
    correlation={
        "parentMessageId": "msg_xyz789",
        "parentChatId": "chat_abc123",
        "parentAssistantId": "assistant_def456",
    },
)
```
```

### Multiple Features Example
```
SDK
What's New

Delete Space - Delete a space (assistant) by ID. Requires manage access.

Example

```python
unique_sdk.Space.delete_space(
    user_id=user_id,
    company_id=company_id,
    space_id="assistant_abc123",
)
```

Get User Groups - Retrieve all groups a user belongs to.

Example

```python
groups = unique_sdk.User.get_user_groups(
    user_id=user_id,
    company_id=company_id,
    target_user_id="123456789",
)
```
```

## Process

1. Check `CHANGELOG.md` for the version being released
2. For each change, read the implementation in `unique_sdk/api_resources/`
3. Write clear, user-friendly descriptions
4. Include practical code examples
5. Use appropriate emoji for change type

