# Contributing to unique_sdk

This guide explains how to implement changes in the SDK, particularly when mirroring public API changes from the monorepo.

## Overview

The `unique_sdk` is a Python SDK that mirrors the public API from the monorepo. Each API resource has its own file, documentation, and follows consistent patterns.

## Cursor Commands

This project includes Cursor commands to automate common tasks:

| Command | Description | When to Use |
|---------|-------------|-------------|
| **Implement API** | Implements public API changes from a PR | When mirroring monorepo API changes |
| **Generate Release Notes** | Creates user-friendly release notes | After implementing changes, before release |

### Using Cursor Commands

Type the command name in the Cursor chat with `@` prefix:

| Command | Usage |
|---------|-------|
| **Implement API** | `@implement-api` + paste the PR diff or the PR link if working with the GitHub MCP |
| **Generate Release Notes** | `@generate-release-notes` + specify the version number |

The commands follow the patterns documented below, ensuring consistency across contributions.

## Project Structure

```
unique_sdk/
├── unique_sdk/
│   ├── api_resources/          # API resource implementations
│   │   ├── _content.py         # Content API
│   │   ├── _message.py         # Message API
│   │   ├── _space.py           # Space API
│   │   ├── _folder.py          # Folder API
│   │   ├── _search.py          # Search API
│   │   ├── _user.py            # User API
│   │   ├── _group.py           # Group API
│   │   ├── _elicitation.py     # Elicitation API
│   │   └── ...
│   ├── utils/                  # Utility functions
│   │   ├── chat_in_space.py    # Chat utilities
│   │   ├── file_io.py          # File upload/download
│   │   └── ...
│   └── __init__.py             # Public exports
├── docs/
│   ├── api_resources/          # API documentation
│   │   ├── content.md
│   │   ├── message.md
│   │   ├── space.md
│   │   └── ...
│   └── utilities/              # Utility documentation
│       ├── chat_in_space.md
│       └── ...
├── tests/                      # Test files
├── pyproject.toml              # Version and dependencies
├── CHANGELOG.md                # Release notes
└── CONTRIBUTING.md             # This file
```

## Mapping Public API to SDK

| Public API Controller | SDK File | Docs File |
|-----------------------|----------|-----------|
| `public-content.controller.ts` | `_content.py` | `content.md` |
| `public-message.controller.ts` | `_message.py` | `message.md` |
| `public-space.controller.ts` | `_space.py` | `space.md` |
| `public-folder.controller.ts` | `_folder.py` | `folder.md` |
| `public-search.controller.ts` | `_search.py` | `search.md` |
| `public-user.controller.ts` | `_user.py` | `user.md` |
| `public-group.controller.ts` | `_group.py` | `group.md` |
| `public-elicitation.controller.ts` | `_elicitation.py` | `elicitation.md` |

Public API location in monorepo:
```
monorepo/next/services/node-chat/src/public-api/2023-12-06/
├── content/
│   └── public-content.controller.ts
├── message/
│   └── public-message.controller.ts
├── space/
│   └── public-space.controller.ts
├── dtos/
│   ├── content/
│   │   └── *.dto.ts
│   ├── message/
│   │   └── *.dto.ts
│   └── space/
│       └── *.dto.ts
└── ...
```

## Implementation Checklist

When implementing a public API change, follow this checklist:

- [ ] **1. Update SDK file** - Add types/methods to `unique_sdk/api_resources/_<resource>.py`
- [ ] **2. Export new types** - Add exports to `unique_sdk/__init__.py` if needed
- [ ] **3. Update documentation** - Add docs to `docs/api_resources/<resource>.md`
- [ ] **4. Bump version** - Increment patch version in `pyproject.toml`
- [ ] **5. Add changelog entry** - Document in `CHANGELOG.md`
- [ ] **6. Generate release notes** - Use the Cursor command to create announcement text
- [ ] **7. Update utilities** - If the change affects utility functions (e.g., `chat_in_space.py`)
- [ ] **8. Get approval** - Request review from **Data Flow** or **Data Science** team

> **Tip:** Use the **Implement API** Cursor command to automate steps 1-5 when implementing changes from a monorepo PR.

## Guide

### Update the SDK Resource File

Location: `unique_sdk/api_resources/_<resource>.py`

#### Adding a new TypedDict (for new DTOs):

```python
class NewDto(TypedDict):
    requiredField: str
    optionalField: NotRequired[str | None]
```

#### Adding a new parameter to existing Params class:

```python
class ExistingParams(RequestOptions):
    existingField: str
    newField: NotRequired[str | None]  # Add new field
```

#### Adding a new endpoint (sync + async):

```python
@classmethod
def new_method(
    cls,
    user_id: str,
    company_id: str,
    **params: Unpack["ClassName.NewMethodParams"],
) -> "ReturnType":
    return cast(
        "ReturnType",
        cls._static_request(
            "post",  # or "get", "patch", "delete"
            "/endpoint/path",
            user_id,
            company_id,
            params=params,
        ),
    )

@classmethod
async def new_method_async(
    cls,
    user_id: str,
    company_id: str,
    **params: Unpack["ClassName.NewMethodParams"],
) -> "ReturnType":
    return cast(
        "ReturnType",
        await cls._static_request_async(
            "post",
            "/endpoint/path",
            user_id,
            company_id,
            params=params,
        ),
    )
```

### Export New Types (if needed)

Location: `unique_sdk/__init__.py`

If you added a new enum or type that users need to import directly:

```python
from unique_sdk.api_resources._content import NewEnum as NewEnum
```

### Update Documentation

Location: `docs/api_resources/<resource>.md`

#### Add method documentation:

```markdown
??? example "`unique_sdk.Resource.new_method` - Description"

    Brief description of what the method does.

    **Parameters:**

    - `param1` (str, required) - Description
    - `param2` (str, optional) - Description
    - `param3` ([`TypeName`](#typename), optional) - Description with link to type

    **Returns:**

    Returns a [`ReturnType`](#returntype) object.

    **Example:**

    ```python
    result = unique_sdk.Resource.new_method(
        user_id=user_id,
        company_id=company_id,
        param1="value",
    )
    ```
```

#### Add type documentation:

```markdown
#### TypeName {#typename}

??? note "Description of the type"

    **Fields:**

    - `field1` (str, required) - Description
    - `field2` (str | None, optional) - Description

    **Used in:** `Resource.method()`
```

### Bump Version

Location: `pyproject.toml`

Increment the patch version:

```toml
[tool.poetry]
version = "0.10.75"  # Was 0.10.74
```

**Versioning rules:**
- **Patch** (0.10.X): New features, bug fixes, non-breaking changes
- **Minor** (0.X.0): Larger features, minor breaking changes
- **Major** (X.0.0): Major breaking changes

### Add Changelog Entry

Location: `CHANGELOG.md`

Add entry at the top (after the header):

```markdown
## [0.10.75] - 2026-02-02
- Add correlation parameter to Message.create for linking messages to parent messages.
- Add new_method function to Resource API.
```

**Format:**
- Use present tense ("Add", not "Added")
- Be concise but descriptive
- Group related changes in one version

### Generate Release Notes

Use the **Generate Release Notes** Cursor command to create user-friendly release notes for Slack/Teams announcements.

The command will:
1. Read the CHANGELOG.md for the latest version
2. Read the relevant SDK files to understand the features
3. Generate formatted release notes with emojis, descriptions, and code examples

**Example output:**
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
    text="Follow-up message",
    role="ASSISTANT",
    correlation={
        "parentMessageId": "msg_xyz789",
        "parentChatId": "chat_abc123",
    },
)
```
```

### Update Utility Functions (if applicable)

If the change affects utility functions in `unique_sdk/utils/`, update them as well.

Location: `unique_sdk/utils/chat_in_space.py` (or other utility files)

Also update utility documentation in `docs/utilities/`.

## Code Patterns

### TypedDict for Request Parameters

```python
class MethodParams(RequestOptions):
    requiredField: str
    optionalField: NotRequired[str | None]
    listField: NotRequired[List[str] | None]
    dictField: NotRequired[Dict[str, Any] | None]
    nestedField: NotRequired["ClassName.NestedType | None"]
```

### TypedDict for Response Types

```python
class ResponseType(TypedDict):
    id: str
    name: str
    optionalField: str | None
    nestedList: List["ClassName.NestedType"]
```

### HTTP Methods

| HTTP Method | SDK Method | Use Case |
|-------------|------------|----------|
| GET | `_static_request("get", ...)` | Retrieve data |
| POST | `_static_request("post", ...)` | Create/Search |
| PATCH | `_static_request("patch", ...)` | Update |
| DELETE | `_static_request("delete", ...)` | Delete |

### URL Patterns

```python
# Collection endpoint
"/content/search"

# Resource with ID
f"/content/{content_id}"

# Nested resource
f"/content/{content_id}/ingestion-state"

# Space endpoints
f"/space/{space_id}/access"
```

## Testing

Run tests before submitting:

```bash
# Run all tests
poetry run poe test

# Run linting
poetry run poe lint

# Run type checking
poetry run poe typecheck

# Run full CI checks
poetry run poe ci-typecheck
poetry run poe ci-coverage
```

## Review Process

1. Create a feature branch: `feat/add-<feature-name>`
2. Implement changes following this guide
3. Run tests and linting
4. Create PR with clear description
5. Request review from **Data Flow** or **Data Science** team
6. Address review feedback
7. Merge after approval

## Quick Reference

### Files to Update for a New Feature

| Change Type | Files to Update |
|-------------|-----------------|
| New parameter | `_<resource>.py`, `<resource>.md`, `CHANGELOG.md`, `pyproject.toml` |
| New endpoint | `_<resource>.py`, `<resource>.md`, `CHANGELOG.md`, `pyproject.toml`, possibly `__init__.py` |
| New TypedDict | `_<resource>.py`, `<resource>.md`, `CHANGELOG.md`, `pyproject.toml` |
| Utility change | `utils/<file>.py`, `utilities/<file>.md`, `CHANGELOG.md`, `pyproject.toml` |

### Common Imports

```python
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    NotRequired,
    Optional,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
```

## Cursor Commands Reference

### Implement API Command

Location: `.cursor/commands/implement-api.md`

This command automates the implementation of public API changes from monorepo PRs:

1. Provide the PR diff or files from the monorepo or PR link if working with GH MCP
2. The command identifies changes in controllers and DTOs
3. It generates the corresponding SDK code, documentation, version bump, and changelog entry

**Usage:**
- Open Cursor command palette
- Select "Implement API" or describe "implement public API changes"
- Paste the PR diff or reference the PR

### Generate Release Notes Command

Location: `.cursor/commands/generate-release-notes.md`

This command creates user-friendly release notes for announcements:

1. Reads the latest CHANGELOG.md entry
2. Reads the implementation to understand the feature
3. Generates formatted notes with emojis, descriptions, and code examples

**Emoji guide used by the command:**

| Change Type | Emoji |
|-------------|-------|
| New feature | 🚀 |
| New endpoint/method | ✨ |
| Enhancement | 💡 |
| Bug fix | 🐛 |
| Breaking change | ⚠️ |
| Deprecation | 📦 |

## Questions?

Contact the **Data Flow** or **Data Science** team for guidance on SDK changes.
