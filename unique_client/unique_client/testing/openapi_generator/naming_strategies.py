#!/usr/bin/env python3
"""
Naming and Path Strategy Functions

This module contains all the logic for:
- Converting API paths to folder structures
- Generating model names from paths
- Converting OpenAPI types to Python types
- Creating consistent naming conventions

By separating these concerns, different naming strategies can be easily swapped in.
"""

import re
from typing import Any, Protocol, Union

from openapi_pydantic.v3.v3_0 import Schema


class NamingStrategy(Protocol):
    """Protocol defining the interface for naming strategies."""

    def create_folder_structure(self, path: str) -> str:
        """Create hierarchical folder structure from API path."""
        ...

    def folder_path_to_model_name(self, folder_path: str) -> str:
        """Convert folder path to PascalCase model name."""
        ...

    def get_python_type_hint(self, schema: Union[Schema, dict[str, Any], None]) -> str:
        """Convert OpenAPI schema to Python type hint."""
        ...


class DefaultNamingStrategy:
    """Default implementation of naming strategy."""

    def create_folder_structure(self, path: str) -> str:
        """Create hierarchical folder structure, filtering out path parameters."""
        path_segments = [seg for seg in path.strip("/").split("/") if seg]

        parts = []
        for segment in path_segments:
            # Skip path parameters and "public"
            if segment.startswith("{") or segment.lower() == "public":
                continue

            # Convert to snake_case
            normalized = segment.replace("-", "_").replace(".", "_")
            snake_case = re.sub("([a-z0-9])([A-Z])", r"\1_\2", normalized).lower()
            snake_case = re.sub(r"[^a-zA-Z0-9_]", "_", snake_case)

            if snake_case:
                parts.append(snake_case)

        return "/".join(parts)

    def folder_path_to_model_name(self, folder_path: str) -> str:
        """Convert folder path to PascalCase model name."""
        if not folder_path:
            return "Root"

        # Remove method and convert to PascalCase
        path_parts = folder_path.split("/")[:-1]
        if not path_parts:
            return "Root"

        pascal_parts = []
        for part in path_parts:
            words = part.replace("-", "_").split("_")
            pascal_part = "".join(word.capitalize() for word in words if word)
            pascal_parts.append(pascal_part)

        return "".join(pascal_parts)

    def get_python_type_hint(self, schema: Union[Schema, dict[str, Any], None]) -> str:
        """Convert OpenAPI schema to Python type hint."""
        if not schema:
            return "str"

        # Convert Schema to dict if needed
        if isinstance(schema, Schema):
            schema_dict = schema.model_dump(exclude_none=True, by_alias=True)
        elif isinstance(schema, dict):
            schema_dict = schema
        else:
            schema_dict = {"type": "string"}

        schema_type = schema_dict.get("type", "string")

        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list[Any]",
            "object": "dict[str, Any]",
        }

        return type_mapping.get(schema_type, "str")


class CompactNamingStrategy(DefaultNamingStrategy):
    """Alternative naming strategy that creates more compact folder structures."""

    def create_folder_structure(self, path: str) -> str:
        """Create more compact folder structure by filtering more aggressively."""
        path_segments = [seg for seg in path.strip("/").split("/") if seg]

        # More aggressive filtering
        skip_patterns = {"public", "api", "v1", "v2", "v3"}

        parts = []
        for segment in path_segments:
            # Skip path parameters, common API prefixes
            if (
                segment.startswith("{")
                or segment.lower() in skip_patterns
                or segment.lower().endswith("_id")
            ):
                continue

            # Convert to snake_case
            normalized = segment.replace("-", "_").replace(".", "_")
            snake_case = re.sub("([a-z0-9])([A-Z])", r"\1_\2", normalized).lower()
            snake_case = re.sub(r"[^a-zA-Z0-9_]", "_", snake_case)

            if snake_case and len(snake_case) > 1:  # Skip single characters
                parts.append(snake_case)

        return "/".join(parts)


class VerboseNamingStrategy(DefaultNamingStrategy):
    """Alternative naming strategy that preserves more path information."""

    def create_folder_structure(self, path: str) -> str:
        """Create more verbose folder structure preserving more segments."""
        path_segments = [seg for seg in path.strip("/").split("/") if seg]

        parts = []
        for segment in path_segments:
            # Only skip path parameters
            if segment.startswith("{"):
                continue

            # Convert to snake_case but preserve more information
            normalized = segment.replace("-", "_").replace(".", "_")
            snake_case = re.sub("([a-z0-9])([A-Z])", r"\1_\2", normalized).lower()
            snake_case = re.sub(r"[^a-zA-Z0-9_]", "_", snake_case)

            if snake_case:
                parts.append(snake_case)

        return "/".join(parts)

    def folder_path_to_model_name(self, folder_path: str) -> str:
        """Create more descriptive model names."""
        if not folder_path:
            return "Root"

        # Include more path information in model names
        path_parts = folder_path.split("/")
        if len(path_parts) > 1:
            path_parts = path_parts[:-1]  # Remove method

        if not path_parts:
            return "Root"

        # Create longer, more descriptive names
        pascal_parts = []
        for part in path_parts:
            words = part.replace("-", "_").split("_")
            pascal_part = "".join(word.capitalize() for word in words if word)
            pascal_parts.append(pascal_part)

        return "".join(pascal_parts)


# Utility functions that can be used standalone or with strategies
def convert_to_snake_case(name: str) -> str:
    """Convert camelCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_pascal_case(s: str) -> str:
    """Convert string to PascalCase."""
    return "".join(word.capitalize() for word in s.replace("-", "_").split("_"))


def sanitize_python_identifier(name: str) -> str:
    """Ensure a string is a valid Python identifier."""
    # Clean up invalid characters
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)

    # Ensure doesn't start with digit
    if name and name[0].isdigit():
        name = f"_{name}"

    # Ensure not empty
    if not name:
        name = "unnamed"

    return name


# Default strategy instance
default_strategy = DefaultNamingStrategy()

# Alternative strategies
compact_strategy = CompactNamingStrategy()
verbose_strategy = VerboseNamingStrategy()

# Strategy registry for easy access
NAMING_STRATEGIES = {
    "default": default_strategy,
    "compact": compact_strategy,
    "verbose": verbose_strategy,
}


def get_strategy(strategy_name: str = "default") -> NamingStrategy:
    """Get a naming strategy by name."""
    return NAMING_STRATEGIES.get(strategy_name, default_strategy)
