# Testing Guidelines for AI-Written Tests

## Overview

Priorities: **clarity, simplicity, determinism, and purpose**.

---

## 1. Test Naming

- **Files**: `test_<module_or_feature>.py`
- **Functions**: `test_<unit>__<behavior>__<condition>`
- **Mark**: `@pytest.mark.ai` for all AI-generated tests

---

## 2. Test Documentation (Required)

Each test **must** have a concise docstring with three parts:

```python
@pytest.mark.ai
def test_slugify__collapses_spaces__ascii_only() -> None:
    """
    Purpose: Ensure slugify collapses multiple spaces to a single dash and strips non-ASCII.
    Why this matters: Prevents broken URLs and duplicate page keys in routing.
    Setup summary: Provide mixed whitespace and non-ASCII characters; assert normalized slug.
    """
    # Arrange
    raw = "  Ana  María  "
    # Act
    slug = slugify(raw)
    # Assert
    assert slug == "ana-maria"
```

---

## 3. Test Structure

**AAA Pattern**: Arrange – Act – Assert with minimal logic.

**Don'ts:**
- No conditionals/loops (use parametrization)
- Don't assert multiple orthogonal behaviors in one test
- Don't reach across layers (e.g., DB + network)

---

## 4. Fixtures and Test Data

### Principles
1. **Centralize fixtures** in `<domain>_fixtures.py`
2. **Register in conftest.py**: `pytest_plugins = ["tests.fixtures"]`
3. **Return actual objects** with type hints
4. **Modify only what changes** per test

### Example

```python
# fixtures.py
@pytest.fixture
def base_user() -> User:
    return User(id="user-123", name="Test User", email="test@example.com")

# test_user.py
@pytest.mark.ai
def test_user__can_be_admin__with_role_change(base_user: User) -> None:
    """
    Purpose: Verify user role can be elevated to admin.
    Why this matters: Critical for permission management.
    Setup summary: Use base fixture, modify role, assert admin status.
    """
    base_user.role = "admin"
    assert base_user.is_admin() is True
```

---

## 5. Type Hints for Better DX

**Always add type hints** to tests for better IDE support:

```python
from typing import Any
import pytest
from myapp.service import UserService
from myapp.models import User

@pytest.mark.ai
def test_service__creates_user__with_valid_data(
    user_service: UserService,
    base_user_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify user creation with valid data.
    Why this matters: Core business functionality.
    Setup summary: Use service fixture and valid data, assert user created.
    """
    # Arrange
    data: dict[str, Any] = base_user_data
    
    # Act
    user = user_service.create_user(data)
    
    # Assert
    assert isinstance(user, User)
    assert user.email == data["email"]
```

---

## 6. Parametrization

```python
@pytest.mark.parametrize(
    "raw, expected",
    [("  John  ", "john"), ("  JOHN", "john"), ("Jo  hn", "jo-hn")],
    ids=["leading-trailing", "uppercase", "middle-spaces"],
)
@pytest.mark.ai
def test_slugify__normalizes_variants(raw: str, expected: str) -> None:
    """
    Purpose: Table-driven check for whitespace/case variants.
    Why this matters: Ensures consistent normalization.
    Setup summary: Parametrized inputs with expected outputs.
    """
    assert slugify(raw) == expected
```

---

## 7. Mocking with pytest-mock

### Core Principles
1. Use `mocker` fixture (from pytest-mock)
2. Mock at the boundary where function is called
3. Use `spec=True` for type safety
4. Keep assertions minimal
5. Prefer fakes/stubs over mocks when practical

### Basic Mocking

```python
@pytest.mark.ai
def test_fetch_user__calls_api__with_correct_id(mocker) -> None:
    """
    Purpose: Verify fetch_user calls API with correct user ID.
    Why this matters: Ensures proper API integration.
    Setup summary: Mock API call, verify parameters passed.
    """
    mock_api = mocker.patch('myapp.service.api_client.get')
    mock_api.return_value = {"id": "123", "name": "Test"}
    
    service = UserService()
    service.fetch_user("123")
    
    mock_api.assert_called_once_with("/users/123")
```

### Method Mocking

```python
@pytest.mark.ai
def test_user_service__validates_email__before_save(mocker, base_user: User) -> None:
    """Mock specific methods with patch.object."""
    mock_validator = mocker.patch.object(UserService, 'validate_email')
    mock_validator.return_value = True
    
    service = UserService()
    service.save_user(base_user)
    
    mock_validator.assert_called_once_with(base_user.email)
```

### Async Mocking

```python
@pytest.mark.ai
@pytest.mark.asyncio
async def test_async_fetch__handles_timeout__with_retry(mocker) -> None:
    """Use AsyncMock for async functions."""
    mock_fetch = mocker.AsyncMock(side_effect=[asyncio.TimeoutError(), {"data": "ok"}])
    mocker.patch('myapp.service.fetch_data', mock_fetch)
    
    result = await fetch_with_retry()
    
    assert result["data"] == "ok"
    assert mock_fetch.call_count == 2
```

### Common Patterns

```python
# Environment variables
def test_service__uses_env_api_key(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "test-key-123")
    assert Service().api_key == "test-key-123"

# File system
def test_loader__reads_config(tmp_path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text('{"key": "value"}')
    assert load_config(config_file)["key"] == "value"

# Time/datetime
def test_scheduler__runs_at_midnight(mocker) -> None:
    mock_now = mocker.patch('myapp.scheduler.datetime')
    mock_now.now.return_value = datetime(2024, 1, 1, 0, 0, 0)
    assert TaskScheduler().should_run_daily_task() is True
```

---

## 8. Isolation and Determinism

- **No live dependencies**: network, filesystem, or clock
- Use `monkeypatch`, `tmp_path`, `mocker`, fakes/stubs
- Seed RNG, freeze time, avoid sleeps/timeouts
- Use `@pytest.mark.skip` or `@pytest.mark.xfail` for flaky/known-broken tests

---

## 9. Assertions

```python
@pytest.mark.ai
def test_parse_age__raises_on_invalid_input() -> None:
    """Assert type + value for outputs, type + message for exceptions."""
    with pytest.raises(ValueError) as exc_info:
        parse_age("NaN")
    assert "integer" in str(exc_info.value).lower()
```

---

## 10. Coverage and Quality

- Target: **≥ 80%** coverage for AI-authored tests
- Use `analyze_coverage.sh` to find untested code

### Running Tests
```bash
pytest -q                                    # All tests
pytest -m ai                                 # AI tests only
pytest --cov=src --cov-report=term-missing  # With coverage
pytest --maxfail=1 --disable-warnings -q    # Fail fast
```

### pytest.ini
```ini
[pytest]
addopts = --strict-markers
asyncio_mode = auto
markers =
    ai: AI-authored test
```

---

## 11. Complete Example

```python
from typing import Any
import pytest
from myapp.service import UserService
from myapp.models import User

@pytest.mark.ai
def test_user_service__creates_user__with_valid_data(
    mocker,
    base_user_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify user creation with validation and data integrity.
    Why this matters: Core business functionality.
    Setup summary: Mock validator and DB, verify user creation flow.
    """
    # Arrange
    mock_validator = mocker.patch('myapp.service.validate_email')
    mock_validator.return_value = True
    mock_db = mocker.patch('myapp.service.database.save')
    mock_db.return_value = User(**base_user_data)
    service: UserService = UserService()
    
    # Act
    user = service.create_user(base_user_data)
    
    # Assert
    assert isinstance(user, User)
    assert user.email == base_user_data["email"]
    mock_validator.assert_called_once_with(base_user_data["email"])
    mock_db.assert_called_once()
```

---

## 12. Quick Reference Checklist

- [ ] Test name: `test_<unit>__<behavior>__<condition>`
- [ ] Marked with `@pytest.mark.ai`
- [ ] Docstring: **Purpose**, **Why this matters**, **Setup summary**
- [ ] Type hints on parameters and return (`-> None`)
- [ ] AAA pattern; no loops/conditionals
- [ ] Centralized fixtures
- [ ] `mocker` fixture with `spec=True` where applicable
- [ ] No live dependencies (deterministic)
- [ ] Precise assertions (type + value)
- [ ] One responsibility per test

---

## 13. Key Takeaways

1. **Fixtures**: Centralize with type hints, modify only what changes
2. **Mocking**: Use `mocker` fixture, mock at boundaries
3. **Type Safety**: Type hints everywhere
4. **AI Marking**: Always use `@pytest.mark.ai`
5. **Documentation**: Clear purpose, impact, setup in every docstring

This creates tests that are **focused, maintainable, type-safe, and well-documented**.
