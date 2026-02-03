---
description: Implement public API changes from a PR in the SDK
---

# Implement Public API Changes from PR

When the user asks to implement public API changes, follow these steps:

## 1. Get PR Information
- Ask user for the PR files/diff if not provided
- The public API is in: `monorepo/next/services/node-chat/src/public-api/2023-12-06/`

## 2. Identify Changes
- Controller files: `*/<resource>/public-<resource>.controller.ts`
- DTO files: `*/dtos/<resource>/*.dto.ts`

## 3. Map to SDK Files

| Public API Controller | SDK File | Docs File |
|-----------------------|----------|-----------|
| public-content.controller.ts | `_content.py` | `content.md` |
| public-message.controller.ts | `_message.py` | `message.md` |
| public-space.controller.ts | `_space.py` | `space.md` |
| public-folder.controller.ts | `_folder.py` | `folder.md` |
| public-search.controller.ts | `_search.py` | `search.md` |
| public-user.controller.ts | `_user.py` | `user.md` |
| public-group.controller.ts | `_group.py` | `group.md` |
| public-elicitation.controller.ts | `_elicitation.py` | `elicitation.md` |

## 4. Implementation Pattern

### For new DTO classes → Add TypedDict:
```python
class NewDto(TypedDict):
    fieldName: str
    optionalField: NotRequired[str | None]
```

### For new endpoint parameters → Update *Params class:
```python
class ExistingParams(RequestOptions):
    existingField: str
    newField: NotRequired[str | None]  # Add new field
```

### For new endpoints → Add sync + async methods:
```python
@classmethod
def new_method(cls, user_id: str, company_id: str, **params: Unpack["Class.Params"]) -> "ReturnType":
    return cast("ReturnType", cls._static_request("post", "/endpoint", user_id, company_id, params=params))

@classmethod
async def new_method_async(cls, user_id: str, company_id: str, **params: Unpack["Class.Params"]) -> "ReturnType":
    return cast("ReturnType", await cls._static_request_async("post", "/endpoint", user_id, company_id, params=params))
```

## 5. Update Documentation
- File: `docs/api_resources/<resource>.md`
- Add method documentation with parameters, returns, and examples
- Add new TypedDict documentation in Input/Return Types section

## 6. Version & Changelog
- Bump patch version in `pyproject.toml`
- Add entry to `CHANGELOG.md`:
```markdown
## [X.Y.Z] - YYYY-MM-DD
- Description of the new feature/change
```

## 7. Checklist
- [ ] SDK file updated with new types/methods
- [ ] Documentation updated
- [ ] Version bumped in pyproject.toml
- [ ] Changelog entry added

