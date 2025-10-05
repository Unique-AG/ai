# Generator Tests

Unit and integration tests for the OpenAPI route generator.

## Running Tests

```bash
# Run all generator tests
poetry run pytest unique_toolkit/generated/generator/tests/

# Run specific test file
poetry run pytest unique_toolkit/generated/generator/tests/test_utils.py

# Run with coverage
poetry run pytest unique_toolkit/generated/generator/tests/ --cov=unique_toolkit.generated.generator

# Run with verbose output
poetry run pytest unique_toolkit/generated/generator/tests/ -v

# Run only AI-generated tests
poetry run pytest unique_toolkit/generated/generator/tests/ -m ai_generated
```

## Test Structure

```
tests/
├── conftest.py                           # Shared fixtures
├── unit/                                 # Unit tests
│   ├── test_utils.py                     # Utility function tests
│   ├── test_schema_generator.py          # Model generation tests
│   ├── test_template_renderer.py         # Jinja2 rendering tests
│   ├── test_init_generator.py            # __init__.py generation tests
│   ├── test_path_processor.py            # Path processing tests
│   └── test_integration.py               # Component integration tests
├── pytest.ini                            # Pytest configuration
└── README.md                             # This file
```

## Test Categories

### Unit Tests
- `test_utils.py` - Path conversion, deduplication, reference resolution
- `test_schema_generator.py` - Pydantic model generation from OpenAPI schemas
- `test_template_renderer.py` - Jinja2 template rendering

### Component Tests  
- `test_init_generator.py` - __init__.py file generation logic
- `test_path_processor.py` - Individual path processing

### Integration Tests
- `test_integration.py` - End-to-end generation pipeline

## Key Test Scenarios

### Covered Scenarios

✅ **Path Conversion**
- CamelCase to snake_case parameter conversion
- Hyphen to underscore in segments
- Path truncation for console output

✅ **Schema Generation**
- Reference resolution ($ref)
- Target class extraction
- Fallback to simple models
- Nested schema handling

✅ **Deduplication**
- Identical class removal
- Conflict detection (same name, different content)
- Content-based comparison

✅ **Template Rendering**
- Endpoint __init__ with operations and subdirs
- Parent __init__ with submodule imports
- API client with path parameters
- Models file with deduplicated classes

✅ **End-to-End**
- Complete file structure generation
- Nested route handling
- Selective path generation
- Error recovery with fallbacks

## Fixtures

### `sample_openapi_spec`
Complete OpenAPI spec with:
- GET /test/endpoint (findAll)
- POST /test/endpoint (create with $ref)
- DELETE /test/endpoint/{itemId} (with path param)
- Component schema: TestResponse

### `template_dir`
Temporary directory with minimal mock templates for isolated testing.

## Writing New Tests

Follow the AAA pattern:

```python
@pytest.mark.ai_generated  
def test_function__behavior__condition(fixture):
    """
    Purpose: What behavior is being verified.
    Why this matters: User-facing or code contract risk.
    Setup summary: Key fixtures or params used.
    """
    # Arrange
    input_data = create_test_data()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_value
```

## Common Assertions

```python
# File existence
assert (path / "models.py").exists()

# Content checks
assert "class CreateResponse(BaseModel):" in content
assert "from .path_operation import" in init_content

# List/dict checks
assert len(result) == 2
assert result["name"] == "Create"

# Pattern matching
assert "Response" in models_content
```

## Mocking Guidelines

Use fixtures for test data, avoid mocking unless necessary:

```python
# ✅ GOOD: Use real objects with fixtures
def test_with_real_objects(sample_openapi_spec):
    processor = PathProcessor(template_dir, output_root, sample_openapi_spec)
    
# ❌ AVOID: Excessive mocking
@patch('module.function1')
@patch('module.function2')  
def test_with_mocks(mock1, mock2):
    # Brittle, tests implementation not behavior
```

## Debugging Failed Tests

```bash
# Run with print statements visible
poetry run pytest unique_toolkit/generated/generator/tests/ -s

# Stop on first failure
poetry run pytest unique_toolkit/generated/generator/tests/ -x

# Run specific test with verbose
poetry run pytest unique_toolkit/generated/generator/tests/test_utils.py::TestTruncatePath::test_truncate_path__adds_ellipsis__when_too_long -v
```

