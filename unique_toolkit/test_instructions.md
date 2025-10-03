# Testing Guidelines

## Core Testing Principles

### 1. Test Naming & Documentation
- **Required Docstring**:
  ```python
  def test_function__behavior__condition():
      """
      Purpose: What behavior is being verified.
      Why this matters: User-facing or code contract risk.
      Setup summary: Key fixtures, mocks, or params used.
      """
  ```

### 2. Test Structure (AAA Pattern)
```python
# Arrange
user = User(name="  Ana María  ")
# Act  
slug = slugify(user.name)
# Assert
assert slug == "ana-maria"
```

**Rules:**
- No conditionals/loops in test bodies
- One responsibility per test
- No cross-layer calls (DB + network in one test)

### 3. Fixture Organization
- **Use single base fixtures** - don't repeat object definitions
- **Modify only what changes** for each test case
- **Return actual objects** with type annotations, not raw dictionaries
- **Centralize in conftest.py** for reuse across test files

### 4. Mocking Best Practices
- **Use `@patch.object()`** instead of complex module patching
- **Mock with actual SDK field names** that your code expects
- **Include required fields** (e.g., `chatId`, `role` for ChatMessage)

```python
# ✅ GOOD: Direct method mocking with proper SDK fields
@patch.object(unique_sdk.Message, 'modify')
def test_modify_message__uses_correct_parameters_AI(mock_modify):
    mock_modify.return_value = {
        "id": "msg123",
        "chatId": "chat123",  # Required field
        "text": "Hello world",
        "role": "USER",       # Required field
    }
```

### 5. Isolation & Determinism
- **No live dependencies** (network, filesystem, clock)
- **Use `monkeypatch`, `tmp_path`, fakes/stubs**
- **Seed randomness** and freeze time to prevent flaky tests

### 6. Assertions & Error Handling
- **Precise assertions** - exact values, not broad matches
- **Exception testing** - assert type + message fragment
```python
with pytest.raises(ValueError) as e:
    parse_age("NaN")
assert "integer" in str(e.value)
```

## Project-Specific Guidelines

### 1. AI Test Marking
```python
@pytest.mark.ai
def test_example_AI():
    """Purpose: ..."""
```

### 2. Fixture Pattern
```python
# ❌ BAD: Repetitive object creation
def test_something():
    event_data = {
        "id": "test-event",
        "userId": "test-user",
        # ... 30+ lines of data
    }
    event = ChatEvent.model_validate(event_data)

# ✅ GOOD: Use base fixture, modify only what changes
def test_something__specific_case_AI(base_chat_event):
    event = base_chat_event
    event.payload.assistant_id = "specific_value"
```

### 3. Common Failures & Solutions

**Pydantic v2 ValidationError:**
```python
# ❌ BAD: Old v1 style
mock_verify.side_effect = ValidationError("Field required")

# ✅ GOOD: v2 style
mock_verify.side_effect = ValidationError.from_exception_data(
    "ValidationError", 
    [{"type": "missing", "loc": ("field",), "msg": "Field required", "input": {}}]
)
```

**Async Decorator Issues:**
```python
# ❌ BAD: Decorator on main function
@async_warning
def to_async(func):
    # ...

# ✅ GOOD: Decorator on inner wrapper
def to_async(func):
    @async_warning
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # ...
```

## Quick Checklist
- [ ] Docstring: Purpose, Why this matters, Setup summary
- [ ] Uses AAA pattern
- [ ] Marked with `@pytest.mark.ai_generated`
- [ ] Uses proper SDK field names in mocks
- [ ] Uses `@patch.object()` for mocking
- [ ] Deterministic (no flaky dependencies)
