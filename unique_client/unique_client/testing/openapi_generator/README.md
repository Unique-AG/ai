# Modular Type-Safe OpenAPI Generator

A clean, modular OpenAPI endpoint generator with pluggable naming strategies and full type safety using BaseEndpoint generics.

## 🏗️ Architecture

This generator uses a **3-layer modular architecture** for maximum flexibility and maintainability:

```
📁 openapi_generator/
├── 📄 README.md                 # This documentation
├── 📄 openapi.json             # OpenAPI 3.0 specification
│
├── 🔧 Core Architecture (3 layers)
│   ├── 📄 model_generator.py      # Low-level model creation utilities  
│   ├── 📄 naming_strategies.py    # Naming and folder structure logic
│   └── 📄 functional_generator.py # High-level orchestration
│
├── 🏗️ Type System
│   └── 📄 endpoint_model.py       # BaseEndpoint with generics
│
├── 📁 generated_endpoints/        # Generated type-safe endpoints
│   ├── 📄 __init__.py            # Auto-generated index
│   ├── 📁 chunk/                 # Endpoint folders by API path
│   ├── 📁 messages/              
│   └── 📁 magic_table/           
│
├── 🧪 Examples & Tests
│   ├── 📄 test.py                # Basic functionality test
│   └── 📄 usage_example.py       # Usage examples with different strategies
```

## 🚀 Quick Start

Generate all endpoints with default naming strategy:
```bash
python functional_generator.py
```

Or use programmatically:
```python
from functional_generator import generate_all_endpoints
from naming_strategies import get_strategy

# Use default strategy
generate_all_endpoints(Path("openapi.json"), Path("."))

# Use specific strategy
strategy = get_strategy("compact")  # or "verbose"
generate_all_endpoints(Path("openapi.json"), Path("."), strategy)
```

## ✨ Key Features

### 🎯 **Type Safety First**
- **BaseEndpoint Generics** - All endpoints inherit type-safe methods
- **TypedDict Path Parameters** - Full IDE autocomplete for URL parameters  
- **Pydantic V2** - Modern validation with `model_validate`
- **Protocol-based Design** - Type-safe interfaces throughout

### 🔧 **Modular Architecture**
- **Pluggable Naming Strategies** - Easy to customize naming conventions
- **Single Responsibility** - Each module has one clear purpose
- **Dependency Injection** - Functions accept strategies as parameters
- **Easy Testing** - Pure functions with clear interfaces

### 📦 **Generated Output**
Each endpoint generates:
- **Minimal Endpoint Class** - Inherits all functionality from BaseEndpoint
- **Request/Response Models** - Pydantic models with validation
- **Path Parameter TypedDict** - Type-safe URL parameter binding
- **Complete Type Safety** - Full IDE support and error detection

## 🎛️ Available Naming Strategies

| Strategy | Description | Example Output |
|----------|-------------|----------------|
| `default` | Balanced approach, filters "public" | `magic_table/cell` → `MagicTableCell` |
| `compact` | Aggressive filtering for shorter names | Similar to default with more filtering |
| `verbose` | Preserves more path information | `public/magic_table/cell` → `PublicMagicTableCell` |

## 🛠️ Creating Custom Strategies

Implement the `NamingStrategy` protocol:

```python
from naming_strategies import DefaultNamingStrategy, NAMING_STRATEGIES

class MyCustomStrategy(DefaultNamingStrategy):
    def create_folder_structure(self, path: str) -> str:
        # Your custom folder logic
        return super().create_folder_structure(path).replace("_", "-")
    
    def folder_path_to_model_name(self, folder_path: str) -> str:
        # Your custom model naming
        base_name = super().folder_path_to_model_name(folder_path)
        return f"My{base_name}"

# Register and use
NAMING_STRATEGIES["custom"] = MyCustomStrategy()
strategy = get_strategy("custom")
```

## 💡 Usage Examples

### Basic Generation
```python
# Generate with different strategies
from functional_generator import generate_all_endpoints
from naming_strategies import get_strategy

# Default strategy
generate_all_endpoints(spec_path, output_dir)

# Compact strategy  
generate_all_endpoints(spec_path, output_dir, get_strategy("compact"))
```

### Using Generated Endpoints
```python
from generated_endpoints.chunk.post import ChunkEndpoint
from generated_endpoints.magic_table.cell.get import (
    MagicTableCellEndpoint, MagicTableCellPathParams
)

# Type-safe request building (inherited from BaseEndpoint)
request = ChunkEndpoint.build_request(title="Test", content="Demo")
response = ChunkEndpoint.parse_response({"id": "chunk_123"})
url = ChunkEndpoint.build_url_with_params()

# Type-safe path parameters with TypedDict
path_params: MagicTableCellPathParams = {"tableId": "my_table"}  
typed_url = MagicTableCellEndpoint.build_url_with_params(**path_params)
```

## 🎉 Benefits

- ✅ **Clean Architecture** - Modular, testable, maintainable
- ✅ **Maximum Type Safety** - Full IDE support and error detection  
- ✅ **No Code Duplication** - All functionality inherited from BaseEndpoint
- ✅ **Easy Customization** - Pluggable naming strategies
- ✅ **Future Proof** - Easy to extend with new features