# SDK Code Generator

Generate type-safe SDK routes from OpenAPI specification.

## Quick Start

```bash
# Generate all routes
poetry run python unique_toolkit/generated/generate_routes.py

# Or use the original script
poetry run python unique_toolkit/generated/separate_routes.py
```

## CLI Usage

### List Available Paths

```bash
poetry run python unique_toolkit/generated/generate_routes.py --list
```

### Generate Specific Path(s)

```bash
# Single path
poetry run python unique_toolkit/generated/generate_routes.py --path "/public/messages"

# Multiple paths
poetry run python unique_toolkit/generated/generate_routes.py \
    --path "/public/messages" \
    --path "/public/folder" \
    --path "/public/content/search"
```

### Generate All Routes

```bash
poetry run python unique_toolkit/generated/generate_routes.py
```

## Features

- ✅ **Descriptive model names** - Based on operationId (e.g., `CreateResponse`, `FindAllResponse`)
- ✅ **Capitalized operations** - `Create`, `FindAll`, `DeleteFolder`
- ✅ **Nested route support** - `unique_SDK.folder.scopeId.DeleteFolder.request()`
- ✅ **Truncated output paths** - Clean console output
- ✅ **Selective generation** - Generate only what you need

## Output Structure

```
generated_routes/
├── public/
│   ├── __init__.py                   # Exposes all submodules
│   ├── messages/
│   │   ├── __init__.py               # Exports Create, FindAll + subdirs
│   │   ├── models.py                 # CreateResponse, FindAllResponse, etc.
│   │   └── path_operation.py        # Create, FindAll operations
│   └── folder/
│       ├── __init__.py
│       ├── models.py
│       ├── path_operation.py
│       └── scopeId/                  # Nested routes
│           ├── __init__.py
│           ├── models.py
│           └── path_operation.py
```

## SDK Usage

```python
import unique_toolkit.generated.generated_routes.public as unique_SDK
from unique_toolkit._common.endpoint_requestor import RequestContext

request_context = RequestContext(headers={...})

# Clean, flat API structure
unique_SDK.folder.CreateFolderStructure.request(
    context=request_context,
    paths=["/test/path"],
)

# Nested routes work naturally
unique_SDK.folder.scopeId.DeleteFolder.request(
    context=request_context,
    scope_id="test",
)
```

## Customization

### Templates

Templates are located in `unique_toolkit/generated/generator/templates/`:
- `endpoint_init_template.jinja2` - Endpoint `__init__.py` files
- `parent_init_template.jinja2` - Parent directory `__init__.py` files  
- `api_template.jinja2` - Operation requestor definitions
- `model_template.jinja2` - Pydantic models

### Modifying Response Names

Response models are named based on the `operationId` in your OpenAPI spec:
- `operationId: "create"` → `CreateResponse`
- `operationId: "findAll"` → `FindAllResponse`

## Troubleshooting

### Missing Response Models

If you see import errors for response models, regenerate all routes:
```bash
poetry run python unique_toolkit/generated/generate_routes.py
```

### Type Checking with Pyright

Pyright is excellent for finding type issues in generated code:

```bash
# Check specific path
pyright unique_toolkit/generated/generated_routes/public/messages/

# Check all generated routes
pyright unique_toolkit/generated/generated_routes/

# With more verbose output
pyright --verbose unique_toolkit/generated/generated_routes/
```

Common issues Pyright finds:
- Missing response models (`CreateResponse`, `UpdateResponse`)
- Duplicate class declarations
- Type inconsistencies
- Import errors

### Automated Quality Check

Use the provided script to check both linting and type errors:

```bash
cd unique_toolkit/generated
./check_generated.sh
```

Or manually:

```bash
# Linter
ruff check unique_toolkit/generated/generated_routes/

# Type checker  
pyright unique_toolkit/generated/generated_routes/
```

## Architecture

The codebase is modularized into components in `generator/`:

### Core Modules
- `path_processor.py` - Process individual OpenAPI paths and generate route files
- `schema_generator.py` - Generate Pydantic models from OpenAPI schemas
- `template_renderer.py` - Jinja2 template rendering
- `init_generator.py` - Generate `__init__.py` files for package structure
- `utils.py` - Helper functions (path conversion, deduplication, reference resolution)

### Templates (`generator/templates/`)
- `model_template.jinja2` - Pydantic model file generation
- `api_template.jinja2` - Operation requestor definitions
- `endpoint_init_template.jinja2` - Endpoint `__init__.py` files
- `parent_init_template.jinja2` - Parent directory `__init__.py` files

This modular architecture enables:
- ✅ Individual path generation
- ✅ Better testability
- ✅ Easy maintenance and feature additions
- ✅ Clear separation of concerns

