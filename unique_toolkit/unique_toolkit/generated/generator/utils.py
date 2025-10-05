"""Utility functions for the route generator."""

import re
from pathlib import Path
from typing import Any, Dict, Union

from openapi_pydantic.v3.v3_1.parameter import Parameter
from openapi_pydantic.v3.v3_1.reference import Reference
from openapi_pydantic.v3.v3_1.request_body import RequestBody
from openapi_pydantic.v3.v3_1.response import Response

# Type alias for JSON-serializable values
JSONValue = Union[Dict[str, Any], list[Any], str, int, float, bool, None]


def truncate_path(path: Path, max_parts: int = 4) -> str:
    """Show last N parts of path with ... prefix if truncated."""
    parts = path.parts
    if len(parts) <= max_parts:
        return str(path)
    return ".../" + "/".join(parts[-max_parts:])


def path_to_folder(path: str) -> Path:
    """Convert an OpenAPI path to a folder path, removing curly braces and sanitizing special chars."""
    segments = []
    for seg in path.strip("/").split("/"):
        # Remove curly braces from path params
        seg = seg.strip("{}")
        # Replace hyphens with underscores and wildcards with 'wildcard'
        seg = seg.replace("-", "_").replace("*", "wildcard")
        segments.append(seg)
    return Path(*segments)


def convert_path_to_snake_case(path: str) -> str:
    """Convert path parameter names from camelCase to snake_case.

    Example: /public/folder/{scopeId} -> /public/folder/{scope_id}
    """

    def camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        # Insert underscore before uppercase letters (except at start)
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        # Insert underscore before uppercase letters preceded by lowercase or numbers
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
        return name.lower()

    # Find all {paramName} patterns and convert them
    def replace_param(match):
        param_name = match.group(1)
        return f"{{{camel_to_snake(param_name)}}}"

    return re.sub(r"\{([^}]+)\}", replace_param, path)


def resolve_refs(schema: Any, spec: Dict[str, Any]) -> JSONValue:
    """Recursively resolve $ref references in a schema."""
    if isinstance(schema, dict):
        if "ref" in schema:  # openapi_pydantic uses 'ref' not '$ref'
            ref_path = schema["ref"].replace("#/", "").split("/")
            resolved = spec
            for part in ref_path:
                resolved = resolved[part]
            return resolve_refs(resolved, spec)
        elif "$ref" in schema:  # Handle both formats
            ref_path = schema["$ref"].replace("#/", "").split("/")
            resolved = spec
            for part in ref_path:
                resolved = resolved[part]
            return resolve_refs(resolved, spec)
        else:
            return {k: resolve_refs(v, spec) for k, v in schema.items()}
    elif isinstance(schema, list):
        return [resolve_refs(item, spec) for item in schema]
    else:
        return schema


def resolve_reference(
    ref_obj: Union[Reference, RequestBody, Response, Parameter, Dict[str, Any]],
    raw_spec: Dict[str, Any],
) -> Union[RequestBody, Response, Parameter, Dict[str, Any], None]:
    """Resolve a Reference object to its actual content.

    If the input is a Reference, resolves it to a Dict from the spec.
    If the input is not a Reference, returns it unchanged (Pydantic model or Dict).
    Returns None if resolution fails.
    """
    if not isinstance(ref_obj, Reference):
        return ref_obj

    try:
        ref_path = ref_obj.ref.replace("#/", "").split("/")
        resolved = raw_spec
        for part in ref_path:
            resolved = resolved[part]
        # When resolving from raw spec, we always get a dict
        return resolved if isinstance(resolved, dict) else None
    except Exception:
        return None


def deduplicate_models(models: list[str]) -> list[str]:
    """Remove duplicate model definitions, keeping the first occurrence.

    Deduplicates based on both class name AND content to catch identical
    definitions generated from the same schema reference.
    """
    seen_classes = {}  # class_name -> normalized_content
    deduplicated = []

    for model in models:
        # Extract class name from the model definition
        class_match = re.match(r"^class\s+(\w+)", model.strip())

        if class_match:
            class_name = class_match.group(1)

            # Normalize the model content for comparison (remove whitespace variations)
            normalized = re.sub(r"\s+", " ", model.strip())

            # Check if we've seen this class name before
            if class_name in seen_classes:
                # Compare the normalized content
                if seen_classes[class_name] == normalized:
                    # Exact duplicate, skip it
                    continue
                else:
                    # Same name but different content - this is a real conflict
                    # Keep the first one and warn
                    print(
                        f"    - Warning: Duplicate class name '{class_name}' with different definitions"
                    )
                    continue
            else:
                # First occurrence of this class
                seen_classes[class_name] = normalized
                deduplicated.append(model)
        else:
            # Not a class definition, keep it
            deduplicated.append(model)

    return deduplicated
