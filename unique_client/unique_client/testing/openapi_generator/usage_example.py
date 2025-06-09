#!/usr/bin/env python3
"""
Usage Example: Flexible OpenAPI Generator with Naming Strategies

This shows how to use the new modular architecture with different naming strategies.
"""

from pathlib import Path

try:
    from unique_client.testing.openapi_generator.functional_generator import (
        generate_all_endpoints,
    )
    from unique_client.testing.openapi_generator.naming_strategies import get_strategy
except ImportError:
    # Fallback for running as script
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from functional_generator import generate_all_endpoints
    from naming_strategies import get_strategy


def main():
    """Examples of using different naming strategies."""
    spec_path = Path("openapi.json")

    if not spec_path.exists():
        print("❌ openapi.json not found")
        return

    print("🚀 FLEXIBLE OPENAPI GENERATOR EXAMPLES")
    print("=" * 50)

    # Example 1: Use default strategy
    print("\n📁 Example 1: Default naming strategy")
    generate_all_endpoints(spec_path, Path("."))  # Uses default strategy

    # Example 2: Use compact strategy explicitly
    print("\n📁 Example 2: Compact naming strategy")
    output_dir = Path("compact_output")
    compact_strategy = get_strategy("compact")
    generate_all_endpoints(spec_path, output_dir, compact_strategy)

    # Example 3: Use verbose strategy
    print("\n📁 Example 3: Verbose naming strategy")
    output_dir = Path("verbose_output")
    verbose_strategy = get_strategy("verbose")
    generate_all_endpoints(spec_path, output_dir, verbose_strategy)

    print("\n✅ All examples completed!")
    print("💡 Check the different output directories to see the naming differences")


# How to create a custom naming strategy:
"""
from unique_client.testing.openapi_generator.naming_strategies import DefaultNamingStrategy

class MyCustomStrategy(DefaultNamingStrategy):
    def create_folder_structure(self, path: str) -> str:
        # Your custom folder logic here
        return super().create_folder_structure(path).replace("_", "-")
    
    def folder_path_to_model_name(self, folder_path: str) -> str:
        # Your custom model naming logic here
        base_name = super().folder_path_to_model_name(folder_path)
        return f"My{base_name}"

# Register your strategy
from unique_client.testing.openapi_generator.naming_strategies import NAMING_STRATEGIES
NAMING_STRATEGIES["custom"] = MyCustomStrategy()

# Use it
custom_strategy = get_strategy("custom")
generate_all_endpoints(spec_path, output_dir, custom_strategy)
"""


if __name__ == "__main__":
    main()
