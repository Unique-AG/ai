# Integration Tests

Integration tests that validate the generated SDK code against the actual Unique API.

## Setup

1. **Copy environment template:**
   ```bash
   cp test.env.example test.env
   ```

2. **Fill in your credentials:**
   ```bash
   # Edit test.env with your values
   UNIQUE_APP_KEY=your_actual_key
   UNIQUE_APP_ID=your_actual_id
   UNIQUE_COMPANY_ID=your_actual_company_id
   UNIQUE_USER_ID=your_actual_user_id
   
   # Existing test resources
   TEST_CHAT_ID=existing_chat_for_testing
   TEST_FOLDER_SCOPE_ID=existing_folder_for_testing
   TEST_ASSISTANT_ID=your_assistant_id
   ```

3. **Run tests:**
   ```bash
   poetry run pytest unique_toolkit/generated/generator/tests/integration/ -v
   ```

## Test Files

### `test_folder_crud.py`
Tests folder CRUD operations:
- Create folder structure
- Update folder properties
- Delete folder
- Get folder info

### `test_messages.py`
Tests message operations:
- Create message
- Find all messages for chat
- Complete message lifecycle (create -> read -> delete)

### `test_search.py`
Tests search functionality:
- Search with query
- String search

## Running Tests

```bash
# Run all integration tests
poetry run pytest unique_toolkit/generated/generator/tests/integration/ -v

# Run specific test file
poetry run pytest unique_toolkit/generated/generator/tests/integration/test_folder_crud.py -v

# Run with output visible
poetry run pytest unique_toolkit/generated/generator/tests/integration/ -v -s

# Skip if test.env missing
poetry run pytest unique_toolkit/generated/generator/tests/integration/ -v
# (tests will auto-skip with helpful message)
```

## Test Patterns

### CRUD Pattern

```python
def test_resource_crud__create_update_delete__succeeds(request_context):
    resource_id = None
    try:
        # Create
        response = unique_SDK.resource.Create.request(context=request_context, ...)
        resource_id = response.id
        
        # Update
        unique_SDK.resource.id.Update.request(
            context=request_context, id=resource_id, ...
        )
        
        # Delete
        unique_SDK.resource.id.Delete.request(
            context=request_context, id=resource_id
        )
        resource_id = None
    finally:
        # Cleanup
        if resource_id:
            unique_SDK.resource.id.Delete.request(...)
```

### Read-Only Pattern

```python
def test_resource_read__retrieves_data__successfully(request_context, integration_env):
    # Use existing resource ID from environment
    resource_id = integration_env["test_resource_id"]
    
    response = unique_SDK.resource.id.Get.request(
        context=request_context, id=resource_id
    )
    
    assert response.id == resource_id
```

## Cleanup

Tests use `cleanup_items` fixture to track created resources:

```python
def test_creates_resource(request_context, cleanup_items):
    response = unique_SDK.resource.Create.request(...)
    cleanup_items.append(("resource", response.id))
    # Cleanup happens automatically in fixture teardown
```

## Skipping Tests

Tests automatically skip if:
- `test.env` file doesn't exist
- Required environment variables are missing
- Required test resource IDs not provided

This prevents failures in CI or local environments without credentials.

## CI Integration

For CI pipelines:

```yaml
# Skip integration tests in CI (they need credentials)
pytest tests/unit/ --ignore=tests/integration/

# Or run integration tests with secrets
pytest tests/integration/ 
  env:
    UNIQUE_APP_KEY: ${{ secrets.UNIQUE_APP_KEY }}
    # ... other secrets
```

## Common Issues

### "No test.env file"
- Copy `test.env.example` to `test.env`
- Fill in your credentials

### "Missing required env vars"
- Check test.env has all UNIQUE_* variables set
- Verify no typos in variable names

### "Resource not found"
- Ensure TEST_CHAT_ID, TEST_FOLDER_SCOPE_ID point to existing resources
- Create test resources in your Unique workspace first

### API Errors
- Verify credentials are valid
- Check base URL is correct for your environment
- Ensure API version matches your setup

