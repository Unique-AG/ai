#!/usr/bin/env python3
"""
Clean OpenAPI Endpoint Generator

Generates minimal, type-safe endpoint classes using BaseEndpoint generics.
All common functionality is inherited from BaseEndpoint.

Uses pluggable naming strategies for maximum flexibility.
"""

import json
from pathlib import Path
from typing import Any

import yaml
from openapi_pydantic.v3.v3_0 import OpenAPI, Operation, Parameter, PathItem

try:
    from unique_client.testing.openapi_generator.model_generator import (
        cleanup_temp_files,
        create_empty_request_model,
        create_empty_success_model,
        create_path_params_typeddict,
        create_request_model,
        create_success_model,
    )
    from unique_client.testing.openapi_generator.naming_strategies import (
        NamingStrategy,
        get_strategy,
    )
except ImportError:
    # Fallback for running as script
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from model_generator import (
        cleanup_temp_files,
        create_empty_request_model,
        create_empty_success_model,
        create_path_params_typeddict,
        create_request_model,
        create_success_model,
    )
    from naming_strategies import NamingStrategy, get_strategy


def load_openapi_spec(spec_path: Path) -> OpenAPI:
    """Load and validate OpenAPI specification."""
    try:
        if spec_path.suffix.lower() in [".yaml", ".yml"]:
            with open(spec_path, "r") as f:
                spec_dict = yaml.safe_load(f)
        else:
            with open(spec_path, "r") as f:
                spec_dict = json.load(f)

        return OpenAPI.model_validate(spec_dict)
    except Exception as e:
        raise ValueError(f"Failed to load OpenAPI spec from {spec_path}: {e}")


def extract_path_parameters(
    operation: Operation, path_item: PathItem
) -> list[Parameter]:
    """Extract path parameters from operation and path item."""
    params = []

    if path_item.parameters:
        params.extend([p for p in path_item.parameters if p.param_in == "path"])

    if operation.parameters:
        params.extend([p for p in operation.parameters if p.param_in == "path"])

    return params


def generate_consolidated_endpoint_file(
    path: str,
    method: str,
    operation: Operation,
    path_item: PathItem,
    endpoint_file: Path,
    naming_strategy: NamingStrategy,
) -> dict[str, Any]:
    """Generate a single consolidated endpoint file with all models."""

    # Generate names using the provided naming strategy
    folder_structure = naming_strategy.create_folder_structure(path)
    folder_path_with_method = (
        f"{folder_structure}/{method}" if folder_structure else method
    )
    base_name = naming_strategy.folder_path_to_model_name(folder_path_with_method)

    # Keep operation_id for endpoint naming
    operation_id = operation.operationId or f"{base_name}_{method}"

    endpoint_info = {
        "path": path,
        "method": method.upper(),
        "operation_id": operation_id,
        "base_name": base_name,
        "models": {},
        "file": str(endpoint_file),
    }

    # Start building file content
    file_content = []
    file_content.append("# Generated endpoint file")
    file_content.append("from __future__ import annotations")
    file_content.append("")
    file_content.append("from typing import Any, Annotated")
    file_content.append("from pydantic import BaseModel, Field, Extra")
    file_content.append("from typing import TypedDict")
    file_content.append("")

    # Add imports for endpoint base classes
    file_content.append(
        "from unique_client.testing.openapi_generator.endpoint_model import BaseEndpoint, NoPathParams"
    )
    file_content.append("")

    # Extract parameters
    path_params = extract_path_parameters(operation, path_item)

    temp_files = []
    try:
        # Generate request model using utility function
        request_type, request_content = create_request_model(
            operation.requestBody, base_name, temp_files
        )
        if request_type:
            file_content.extend(request_content)
            endpoint_info["models"]["request"] = {"name": request_type}

        # Generate success response model using utility function
        success_type, success_content, status_code = create_success_model(
            operation.responses, base_name, temp_files
        )
        if success_type:
            file_content.extend(success_content)
            endpoint_info["models"]["success"] = {
                "name": success_type,
                "status_code": status_code,
            }

    finally:
        # Clean up temp files using utility function
        cleanup_temp_files(temp_files)

    # Generate typed endpoint class
    file_content.append("")
    file_content.append("# Type-safe endpoint class")
    endpoint_class_name = f"{base_name}Endpoint"

    # Generate TypedDict for path parameters using utility function
    path_params_type, path_params_content = create_path_params_typeddict(
        path_params, base_name, method, path, naming_strategy
    )
    file_content.extend(path_params_content)

    # Determine generic type parameters
    request_type = endpoint_info["models"].get("request", {}).get("name")
    success_type = endpoint_info["models"].get("success", {}).get("name")

    # Create empty models if none exist using utility functions
    if not request_type:
        request_type, request_content = create_empty_request_model(
            base_name, method, path
        )
        file_content.extend(request_content)

    if not success_type:
        success_type, success_content = create_empty_success_model(
            base_name, method, path
        )
        file_content.extend(success_content)

    # Generate the endpoint class
    file_content.append(
        f"class {endpoint_class_name}(BaseEndpoint[{request_type}, {success_type}, {path_params_type}]):"
    )
    file_content.append(f'    """Type-safe endpoint for {method.upper()} {path}"""')
    file_content.append("")
    file_content.append(f'    path: str = "{path}"')
    file_content.append(f'    method: str = "{method.upper()}"')
    file_content.append(f'    operation_id: str = "{operation_id}"')
    file_content.append("")

    # Set model classes and path parameter names - BaseEndpoint handles the rest!
    file_content.append(f"    request_model: type[{request_type}] = {request_type}")
    file_content.append(f"    response_model: type[{success_type}] = {success_type}")

    # Add path parameter names for proper request building
    if path_params:
        path_param_names = [param.name for param in path_params]
        file_content.append(f"    path_param_names: list[str] = {path_param_names}")

    file_content.append("")

    # Create endpoint instance
    file_content.append("# Endpoint instance")
    constructor_args = []
    constructor_args.append(f'path="{path}"')
    constructor_args.append(f'method="{method.upper()}"')
    constructor_args.append(f'operation_id="{operation_id}"')
    constructor_args.append(f"request_model={request_type}")
    constructor_args.append(f"response_model={success_type}")

    if path_params:
        path_param_names = [param.name for param in path_params]
        constructor_args.append(f"path_param_names={path_param_names}")

    args_str = ",\n    ".join(constructor_args)
    file_content.append(f"{base_name}Endpoint = {endpoint_class_name}(")
    file_content.append(f"    {args_str}")
    file_content.append(")")

    # Write consolidated file
    endpoint_file.parent.mkdir(parents=True, exist_ok=True)
    with open(endpoint_file, "w") as f:
        f.write("\n".join(file_content))

    print(f"📝 Generated: {endpoint_file}")
    return endpoint_info


def generate_index_file(endpoints: dict[str, dict[str, Any]], output_dir: Path) -> None:
    """Generate index file for all endpoints."""
    index_file = output_dir / "generated_endpoints" / "__init__.py"
    index_file.parent.mkdir(parents=True, exist_ok=True)

    index_content = []
    index_content.append('"""Generated consolidated endpoint instances."""')
    index_content.append("")

    # Group by folder structure
    endpoint_groups = {}
    for endpoint_key, endpoint_info in endpoints.items():
        parts = endpoint_key.split("/")
        if len(parts) > 1:
            folder_path = "/".join(parts[:-1])
            method = parts[-1]
            if folder_path not in endpoint_groups:
                endpoint_groups[folder_path] = []
            endpoint_groups[folder_path].append((method, endpoint_info))
        else:
            if "root" not in endpoint_groups:
                endpoint_groups["root"] = []
            endpoint_groups["root"].append((endpoint_key, endpoint_info))

    # Generate imports
    all_endpoints = []
    for folder_path, methods in sorted(endpoint_groups.items()):
        if folder_path == "root":
            index_content.append("# Root level endpoints")
            for method, endpoint_info in methods:
                base_name = endpoint_info["base_name"]
                endpoint_var_name = f"{base_name}Endpoint"
                index_content.append(f"from .{method} import {endpoint_var_name}")
                all_endpoints.append(endpoint_var_name)
        else:
            index_content.append(f"# {folder_path.replace('/', ' > ')} endpoints")
            for method, endpoint_info in methods:
                base_name = endpoint_info["base_name"]
                endpoint_var_name = f"{base_name}Endpoint"
                import_path = folder_path.replace("/", ".")
                index_content.append(
                    f"from .{import_path}.{method} import {endpoint_var_name}"
                )
                all_endpoints.append(endpoint_var_name)
        index_content.append("")

    # Generate __all__ list
    index_content.append("# All endpoint instances")
    index_content.append("__all__ = [")
    for endpoint_name in all_endpoints:
        index_content.append(f'    "{endpoint_name}",')
    index_content.append("]")

    with open(index_file, "w") as f:
        f.write("\n".join(index_content))

    print(f"📄 Generated index: {index_file}")


def generate_all_endpoints(
    spec_path: Path, output_dir: Path, naming_strategy: NamingStrategy | None = None
) -> None:
    """Main function to generate all endpoints."""
    print("🚀 Starting functional OpenAPI endpoint generation...")

    # Use default strategy if none provided
    if naming_strategy is None:
        naming_strategy = get_strategy("default")

    # Load OpenAPI spec
    spec = load_openapi_spec(spec_path)

    all_endpoints = {}
    generated_endpoints_dir = output_dir / "generated_endpoints"

    # Process each path and method
    for path, path_item in spec.paths.items():
        for method_name, operation in [
            ("get", path_item.get),
            ("post", path_item.post),
            ("put", path_item.put),
            ("patch", path_item.patch),
            ("delete", path_item.delete),
            ("head", path_item.head),
            ("options", path_item.options),
            ("trace", path_item.trace),
        ]:
            if not operation:
                continue

            print(f"📝 Processing {method_name.upper()} {path}")

            # Create folder structure using the naming strategy
            folder_structure = naming_strategy.create_folder_structure(path)
            if folder_structure:
                endpoint_dir = generated_endpoints_dir / folder_structure
            else:
                endpoint_dir = generated_endpoints_dir / "root"

            endpoint_file = endpoint_dir / f"{method_name}.py"

            # Generate consolidated endpoint file
            endpoint_info = generate_consolidated_endpoint_file(
                path, method_name, operation, path_item, endpoint_file, naming_strategy
            )

            # Store with folder/method key
            endpoint_key = (
                f"{folder_structure}/{method_name}" if folder_structure else method_name
            )
            all_endpoints[endpoint_key] = endpoint_info

    # Generate index file
    generate_index_file(all_endpoints, output_dir)

    print(f"✅ Generated {len(all_endpoints)} endpoints")
    print("🎉 Functional generation completed!")


def main(strategy_name: str = "default") -> None:
    """Main entry point with configurable naming strategy."""
    spec_path = Path("openapi.json")
    output_dir = Path(".")

    if not spec_path.exists():
        print(f"❌ OpenAPI spec not found: {spec_path}")
        return

    # Get the requested naming strategy
    naming_strategy = get_strategy(strategy_name)
    print(f"🎯 Using '{strategy_name}' naming strategy")

    generate_all_endpoints(spec_path, output_dir, naming_strategy)


if __name__ == "__main__":
    main()
