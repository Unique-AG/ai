# Comprehensive Testing Guidelines

## Overview

This document combines comprehensive testing guidelines for AI-written tests with specific refactoring instructions for our codebase. The priorities are **clarity, simplicity, determinism, and purpose**.

---

## 1. Test Naming Conventions

### Files
- **Files:** `test_<module_or_feature>.py`

### Functions
- **Functions:** `test_<unit_under_test>__<behavior>__<condition>_<AI_SUFFIX>`
- The **AI suffix is mandatory**: end the name with **`_AI`** or **`_AI_WRITTEN`** (uppercase)
- Examples:
  - `test_parse_user__strips_whitespace__happy_path_AI`
  - `test_fetch_profile__raises_on_404__network_error_AI_WRITTEN`

> **Rationale:** Easy grepping/filtering for AI-authored tests and consistent behavior-focused style.

---

## 2. Test Documentation (Required)

Each test **must** start with a concise docstring explaining **why the test exists** and **how it creates confidence**.

**Template:**
```python
def test_<...>_AI():
    """
    Purpose: One or two sentences on what behavior or contract is being verified.
    Why this matters: One sentence tying to a user-facing or code contract risk.
    Setup summary: What is arranged, including key fixtures, mocks, or params.
    """
    ...
```

**Example:**
```python
def test_slugify__collapses_spaces__ascii_only_AI():
    """
    Purpose: Ensure slugify collapses multiple spaces to a single dash and strips non-ASCII.
    Why this matters: Prevents broken URLs and duplicate page keys in routing.
    Setup summary: Provide mixed whitespace and non-ASCII characters; assert normalized slug.
    """
    ...
```

---

## 3. Test Structure (AAA Pattern)

Use **Arrange – Act – Assert** with minimal logic in the test body.

```python
# Arrange
user = User(name="  Ana María  ")
# Act
slug = slugify(user.name)
# Assert
assert slug == "ana-maria"
```

**Don'ts:**
- Don't have conditionals/loops in test bodies unless parametrization would be worse
- Don't assert multiple orthogonal behaviors in one test—split into separate tests
- Don't reach across layers (e.g., call the DB and the network) in a single unit test

---

## 4. Key Principles for Test Organization

### 1. Use Single Base Fixtures
- **Instead of defining the same event/object over and over**, use a single base fixture
- **Manipulate only what you need to change** in each test
- This eliminates repetitive code and makes tests more maintainable

### 2. Centralize Test Data
- **Collect fixtures under a dedicated file** (e.g., `fixtures.py`)
- **Register fixtures in conftest.py** so they're available to all test files
- Use descriptive names like `fixtures.py` instead of `test_data.py`

### 3. Return Actual Objects, Not Raw Data
- **Fixtures should return actual ChatEvent/Event objects**, not raw dictionaries
- **Add proper type annotations** to all fixtures
- This provides better type safety and IDE support

### 4. Focus on What Each Test Actually Tests
- **Only modify the specific fields** that are relevant to the test case
- **Don't repeat the entire object structure** in each test
- Make it clear what makes each test unique

### 5. Use Simple Mocking Patterns
- **Avoid complex module-level patching** - use `@patch.object()` instead
- **Mock only what you need** - don't patch entire modules when you only need specific methods
- **Use direct method mocking** for cleaner, more focused tests

### 6. Use Proper SDK Types in Mocks
- **Mock with actual SDK field names** that your code expects
- **Use the same structure** as the real SDK responses
- **Include required fields** that your domain objects need (e.g., `chatId`, `role`)

### 7. Mark AI-Generated Tests
- **Always add `@pytest.mark.ai`** to AI-authored tests (individual functions or classes)
- **Use the marker on test functions/classes** for easy filtering
- **This enables filtering** with `pytest -m ai` or `pytest -m "not ai"`
- **Alternative markers:** `@pytest.mark.ai_generated` for test classes created by AI

---

## 5. Fixtures and Test Data Management

### Use Single Base Fixtures
- **Instead of defining the same event/object over and over**, use a single base fixture
- **Manipulate only what you need to change** in each test
- This eliminates repetitive code and makes tests more maintainable

### Centralize Test Data
- **Collect fixtures under a dedicated file** (e.g., `fixtures.py`)
- **Register fixtures in conftest.py** so they're available to all test files
- Use descriptive names like `fixtures.py` instead of `test_data.py`

### Return Actual Objects, Not Raw Data
- **Fixtures should return actual ChatEvent/Event objects**, not raw dictionaries
- **Add proper type annotations** to all fixtures
- This provides better type safety and IDE support

### Fixture Naming and Scope
- **Naming:** nouns, lowercase with underscores (e.g., `tmp_user`, `client`, `fake_repo`)
- **Scope:** default to `function`; escalate to `module`/`session` only for expensive immutables
- **Determinism:** seed randomness inside fixtures

**Example `conftest.py`:**
```python
# conftest.py
import os
import random
import pytest

@pytest.fixture(autouse=True)
def _seed_random():
    random.seed(1337)

@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path

@pytest.fixture
def fake_repo():
    class FakeRepo:
        def __init__(self): self.saved = []
        def save(self, x): self.saved.append(x)
    return FakeRepo()
```

---

## 6. Implementation Pattern

### Before (Bad):
```python
def test_something(self):
    event_data = {
        "id": "test-event",
        "event": "unique.chat.external-module.chosen",
        "userId": "test-user",
        # ... 30+ lines of repetitive data
    }
    event = ChatEvent.model_validate(event_data)
    # test logic
```

### After (Good):
```python
@pytest.mark.ai
def test_something__handles_specific_case__with_valid_data_AI(base_chat_event_data: ChatEvent):
    """
    Purpose: Verify specific behavior with valid input data.
    Why this matters: Ensures the function handles expected input correctly.
    Setup summary: Use base fixture and modify only necessary fields.
    """
    # Modify only what needs to change for this test
    event = base_chat_event_data
    event.payload.assistant_id = "specific_value"
    # test logic
```

---

## 7. Parametrization and Test Data

### Use Parametrization Over Loops
Use `@pytest.mark.parametrize` for input–output tables.

```python
import pytest

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  John  ", "john"),
        ("  JOHN", "john"),
        ("Jo  hn", "jo-hn"),
    ],
)
@pytest.mark.ai
def test_slugify__normalizes_common_cases_AI(raw, expected):
    """
    Purpose: Table-driven check for typical whitespace/case variants.
    Why this matters: Ensures consistent normalization across different input formats.
    Setup summary: Parametrized inputs with expected outputs.
    """
    assert slugify(raw) == expected
```

---

## 8. Mocking Best Practices

### Mocking Guidelines
- Prefer **fakes** over deep mocks; patch at the **boundary** you own
- Patch where the symbol is **looked up**, not where it's defined
- Keep expectations minimal: assert **what matters**, not every call
- When using `MagicMock` define the spec so there is type hints

### ❌ Avoid Complex Module Patching
```python
# BAD: Complex fixture that patches entire module
@pytest.fixture
def mock_sdk():
    with patch("unique_toolkit.chat.functions.unique_sdk") as mock:
        yield mock

def test_modify_message(mock_sdk, sample_message_data):
    mock_sdk.Message.modify.return_value = sample_message_data
    # ... test logic
```

### ✅ Use Simple Method Mocking
```python
# GOOD: Direct method mocking
@patch.object(unique_sdk.Message, 'modify')
@pytest.mark.ai
def test_modify_message__uses_correct_parameters__with_valid_data_AI(mock_modify, sample_message_data):
    """
    Purpose: Ensure modify method is called with correct parameters.
    Why this matters: Validates the integration between our code and SDK.
    Setup summary: Mock the SDK method and verify call parameters.
    """
    mock_modify.return_value = sample_message_data
    # ... test logic
```

### ❌ Avoid Raw Dictionary Mocks
```python
# BAD: Generic field names that don't match SDK
@pytest.fixture
def sample_message_data():
    return {
        "user_id": "user123",
        "company_id": "company123",
        "content": "Hello world",
        # Missing required fields like chatId, role
    }
```

### ✅ Use Proper SDK Field Names
```python
# GOOD: Field names that match what SDK actually returns
@pytest.fixture
def sample_message_data():
    return {
        "id": "msg123",
        "chatId": "chat123",  # Required field for ChatMessage
        "text": "Hello world",
        "role": "USER",  # Required field for ChatMessage
        "gptRequest": None,
        "debugInfo": None,
    }
```

---

## 9. Isolation and Side Effects

### No Live Dependencies
- **No live network, filesystem, or clock** in unit tests
- Use `monkeypatch`, `tmp_path`, and fakes/stubs
- For time: patch time sources (e.g., function returning `datetime.now()`), or use injectable clock

```python
@pytest.mark.ai
def test_service__uses_env_api_key_AI(monkeypatch):
    """
    Purpose: Validate API key resolution from environment for security.
    Why this matters: Ensures proper configuration handling and security.
    Setup summary: Mock environment variable and verify service initialization.
    """
    monkeypatch.setenv("API_KEY", "k-123")
    assert Service().api_key == "k-123"
```

---

## 10. Assertions and Error Handling

### Precise Assertions
- Prefer **exact** assertions over broad ones
- Assert **type + value** for structured outputs; match error **type + message fragment** for exceptions

```python
@pytest.mark.ai
def test_parse_age__raises_on_invalid_input__with_non_numeric_AI():
    """
    Purpose: Ensure parse_age raises appropriate error for invalid input.
    Why this matters: Prevents silent failures and provides clear error messages.
    Setup summary: Provide invalid input and assert specific exception type and message.
    """
    with pytest.raises(ValueError) as e:
        parse_age("NaN")
    assert "integer" in str(e.value)
```

---

## 11. Determinism and Flakiness

### Prevent Flaky Tests
- Seed RNG, freeze time (via patch), and avoid timeouts/sleeps
- Any retry logic must be tested with controlled fakes, not actual waiting
- If a legitimate flaky external dependency exists, **skip** with rationale and an issue reference

```python
import pytest

@pytest.mark.skip(reason="Relies on external service; covered by contract tests in CI: #1234")
@pytest.mark.ai
def test_external_contract_AI():
    """
    Purpose: Documented skip until service provides sandbox.
    Why this matters: Prevents flaky tests while maintaining test coverage documentation.
    Setup summary: N/A - test is skipped with clear rationale.
    """
    ...

@pytest.mark.xfail(reason="Bug #567: slugify doesn't collapse Unicode spaces", strict=True)
@pytest.mark.ai
def test_slugify__unicode_spaces_AI():
    """
    Purpose: Document known bug behavior until fix is implemented.
    Why this matters: Locks current failing behavior and tracks known issues.
    Setup summary: Test current (incorrect) behavior with Unicode spaces.
    """
    ...
```

---

## 12. File Organization

### fixtures.py
- Contains all base fixtures with proper type annotations
- Single source of truth for test data
- Reusable across multiple test files

### conftest.py
- Imports and registers fixtures from fixtures.py
- Makes fixtures available to all test files automatically
- Contains global fixtures like random seeding

### Individual test files
- Import fixtures from conftest.py (no explicit imports needed)
- Focus on test logic, not data setup
- Modify only what's necessary for each test case

---

## 13. Coverage and Quality Gates

### Coverage Targets
- Target coverage for AI-authored tests: **≥ 80%** of touched modules
- CI runs:
  - `pytest -q`
  - `pytest --maxfail=1 --disable-warnings -q`
  - `pytest --cov=src --cov-report=term-missing`

### Marks and Selectors
Add a global mark to AI-authored tests for targeted runs:

```python
# in pytest.ini
[pytest]
markers =
    ai: "AI-authored test"
```

Then mark tests:
```python
import pytest

@pytest.mark.ai
def test_example_AI():
    """Purpose: ..."""
    ...
```

- Run subsets: `pytest -m ai` or exclude: `pytest -m "not ai"`

---

## 14. Complete Example

```python
import pytest
from mypkg.text import slugify

@pytest.mark.ai
def test_slugify__removes_non_alnum__keeps_dashes_AI():
    """
    Purpose: Verify slugify strips non-alphanumeric chars but preserves single dashes.
    Why this matters: Prevents broken routes and aligns with SEO URL policy.
    Setup summary: Provide mixed punctuation; expect cleaned, lowercase output with dashes intact.
    """
    # Arrange
    raw = "Hello, World!!  v2.0 -- release"
    # Act
    out = slugify(raw)
    # Assert
    assert out == "hello-world-v2-0-release"
```

---

## 15. Benefits

1. **DRY (Don't Repeat Yourself)**: Eliminates hundreds of lines of repetitive code
2. **Maintainability**: Changes to base data only need to be made in one place
3. **Clarity**: Each test clearly shows what it's testing
4. **Type Safety**: Proper type annotations catch errors early
5. **Reusability**: Fixtures can be shared across test files
6. **Consistency**: All tests use the same base structure
7. **Simpler Mocking**: Direct method mocking is easier to understand and maintain
8. **Realistic Testing**: Using proper SDK field names makes tests more realistic
9. **Deterministic**: Seeded randomness and controlled time prevent flaky tests
10. **Well-Documented**: Clear docstrings explain the purpose and value of each test

---

## 16. Quick Checklist (for AI)

- [ ] Function name ends with `_AI` or `_AI_WRITTEN` (uppercase)
- [ ] Docstring includes **Purpose**, **Why this matters**, **Setup summary**
- [ ] Uses AAA; no loops/conditionals in body (prefer parametrization)
- [ ] Deterministic (seeded/randomness mocked; time/network/files patched)
- [ ] Assertions are precise; exceptions assert type + message fragment
- [ ] Uses fixtures for setup; scope correct
- [ ] Marked with `@pytest.mark.ai` if applicable
- [ ] Keeps one responsibility per test
- [ ] Uses proper SDK field names in mocks
- [ ] Avoids complex module patching in favor of direct method mocking

---

## 17. Key Takeaways

### 1. Fixture Organization
**"Instead of defining the event over and over, use a single chat event fixture and then eventually manipulate only what we need to change in the test"**

### 2. Mocking Strategy
**"Don't patch entire modules when you only need to mock specific methods - use `@patch.object()` for focused, simple mocking"**

### 3. SDK Compatibility
**"Mock with the actual field names that your domain objects expect - this makes tests more realistic and catches integration issues early"**

### 4. AI Test Identification
**"Always mark AI-authored tests with `@pytest.mark.ai` to enable filtering and tracking of AI vs human-written tests"**

### 5. Test Documentation
**"Every test must have a clear docstring explaining its purpose, why it matters, and what setup is involved"**

This comprehensive approach transforms tests from being data-heavy and repetitive to being focused, maintainable, realistic, and well-documented.
