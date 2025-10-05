# Integration Tests

Integration tests that validate the generated SDK code against the actual Unique API.

## ⚠️ Important: Regenerate Routes First

Before running integration tests, regenerate all routes with the latest generator:

```bash
cd unique_toolkit/generated
poetry run python generate_routes.py
```

This ensures all operations have correct type signatures and parameter names.

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
   TEST_CONTENT_ID=existing_content_for_testing
   TEST_MESSAGE_ID=existing_message_for_testing
   TEST_TABLE_ID=existing_table_for_testing
   ```

3. **Run tests:**
   ```bash
   poetry run pytest unique_toolkit/generated/generator/tests/integration/ -v
   ```

## Test Files

### CRUD Operations
- **test_folder_crud.py** - Folder create/update/delete cycle
- **test_messages.py** - Message lifecycle (create -> read -> delete)
- **test_content.py** - Content upsert and deletion
- **test_chunk.py** - Chunk creation (single and batch)
- **test_short_term_memory.py** - Memory create and find latest
- **test_magic_table.py** - Table operations (rows, cells)

### Read-Only Operations
- **test_search.py** - Search and search-string operations  
- **test_company.py** - Company resources (acronyms)
- **test_openai_proxy.py** - OpenAI completions and embeddings

### Other Operations
- **test_message_assessment.py** - Message assessment CRUD
- **test_message_log.py** - Message execution logging
- **test_agent.py** - Agent execution
- **test_mcp.py** - MCP tool calling
- **test_space.py** - Space and chat management

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

## Verifying Test Code Before Running

Use pyright to check for parameter errors:

```bash
# Check all integration tests
pyright unique_toolkit/generated/generator/tests/integration/

# Check specific file
pyright unique_toolkit/generated/generator/tests/integration/test_messages.py
```

Common issues:
- "No parameter named X" - Routes need regeneration
- "is not a known attribute" - Operation name incorrect or route not generated
- Missing required parameters - Check the generated models for required fields

## Test Patterns

### CRUD Pattern

```python
def test_resource_crud__create_update_delete__succeeds(request_context):
    resource_id = None
    try:
        # Create
        response = unique_SDK.resource.Create.request(
            context=request_context,
            field1="value1",  # Use snake_case field names
            field2="value2",
        )
        resource_id = response.id if hasattr(response, "id") else response.get("id")
        
        # Update
        unique_SDK.resource.id.Update.request(
            context=request_context, 
            id=resource_id,
            field1="updated_value",
        )
        
        # Delete
        unique_SDK.resource.id.Delete.request(
            context=request_context, 
            id=resource_id
        )
        resource_id = None
    finally:
        # Cleanup
        if resource_id:
            unique_SDK.resource.id.Delete.request(
                context=request_context,
                id=resource_id
            )
```

### Read-Only Pattern

```python
def test_resource_read__retrieves_data__successfully(request_context, integration_env):
    # Use existing resource ID from environment
    resource_id = integration_env["test_resource_id"]
    if not resource_id:
        pytest.skip("TEST_RESOURCE_ID required")
    
    response = unique_SDK.resource.id.Get.request(
        context=request_context, 
        id=resource_id
    )
    
    assert response is not None
```

## Cleanup

Tests use `cleanup_items` fixture to track created resources:

```python
def test_creates_resource(request_context, cleanup_items):
    response = unique_SDK.resource.Create.request(context=request_context, ...)
    resource_id = response.id if hasattr(response, "id") else response.get("id")
    cleanup_items.append(("resource", resource_id))
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

### "No parameter named X"
- **Solution:** Regenerate all routes first:
  ```bash
  poetry run python unique_toolkit/generated/generate_routes.py
  ```
- This happens when routes were generated before the latest generator improvements

### "Operation is not a known attribute"
- Check operation name capitalization matches generated code
- Verify the endpoint path exists in OpenAPI spec
- Regenerate routes if operation was recently added
