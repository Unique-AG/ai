#!/usr/bin/env python3
"""Generate SDK routes from OpenAPI spec.

Usage:
    # Generate all routes
    python generate_routes.py

    # Generate specific path only
    python generate_routes.py --path "/public/messages"

    # Generate multiple specific paths
    python generate_routes.py --path "/public/messages" --path "/public/folder"

    # List available paths
    python generate_routes.py --list
"""

import argparse
import json
from pathlib import Path

from openapi_pydantic import OpenAPI


def list_paths(openapi_path: Path) -> None:
    """List all available paths in the OpenAPI spec."""
    with openapi_path.open("r") as f:
        raw_spec = json.load(f)

    openapi = OpenAPI.model_validate(raw_spec)

    if not openapi.paths:
        print("No paths found in OpenAPI spec")
        return

    print("Available paths:")
    for path in sorted(openapi.paths.keys()):
        methods = []
        path_item = openapi.paths[path]
        if path_item.get:
            methods.append("GET")
        if path_item.post:
            methods.append("POST")
        if path_item.put:
            methods.append("PUT")
        if path_item.delete:
            methods.append("DELETE")
        if path_item.patch:
            methods.append("PATCH")

        print(f"  {path:50} [{', '.join(methods)}]")


def generate_specific_paths(
    openapi_path: Path, output_root: Path, paths: list[str]
) -> None:
    """Generate routes for specific paths only."""
    import json

    from openapi_pydantic import OpenAPI

    from unique_toolkit.generated.generator import (
        InitGenerator,
        PathProcessor,
        generate_components_file,
    )

    print(f"Generating routes for {len(paths)} path(s)...")

    # Load OpenAPI spec
    with openapi_path.open("r") as f:
        raw_spec = json.load(f)

    openapi = OpenAPI.model_validate(raw_spec)

    if not openapi.paths:
        print("Error: No paths found in OpenAPI spec")
        return

    # Filter to only requested paths
    paths_to_generate = {
        path: path_item for path, path_item in openapi.paths.items() if path in paths
    }

    if not paths_to_generate:
        print("Warning: None of the specified paths found in OpenAPI spec")
        print(f"Available paths: {list(openapi.paths.keys())[:5]}...")
        return

    # Initialize template directory
    template_dir = Path(__file__).parent / "generator" / "templates"

    # STEP 1: Generate components file first
    print("\n🔧 Generating component schemas...")
    generate_components_file(raw_spec, output_root, template_dir)

    # STEP 2: Process each path (they can now import from components)
    processor = PathProcessor(template_dir, output_root, raw_spec)
    for path, path_item in paths_to_generate.items():
        processor.process_path(path, path_item)

    # STEP 3: Update __init__.py files
    init_generator = InitGenerator(template_dir)
    init_generator.update_endpoint_init_files(output_root)
    init_generator.generate_parent_init_files(output_root)

    print("\n✅ Generation complete!")


def generate_all_routes() -> None:
    """Generate all routes (original behavior)."""
    import json

    from openapi_pydantic import OpenAPI

    from unique_toolkit.generated.generator import (
        InitGenerator,
        PathProcessor,
        generate_components_file,
    )

    openapi_path = Path(__file__).parent / "openapi.json"
    output_root = Path(__file__).parent / "generated_routes"

    print("Generating all routes...")

    # Load OpenAPI spec
    with openapi_path.open("r") as f:
        raw_spec = json.load(f)

    openapi = OpenAPI.model_validate(raw_spec)

    if not openapi.paths:
        print("Error: No paths found in OpenAPI spec")
        return

    # Initialize template directory
    template_dir = Path(__file__).parent / "generator" / "templates"

    # STEP 1: Generate components file first
    print("\n🔧 Generating component schemas...")
    generate_components_file(raw_spec, output_root, template_dir)

    # STEP 2: Process all paths (they can now import from components)
    processor = PathProcessor(template_dir, output_root, raw_spec)
    for path, path_item in openapi.paths.items():
        processor.process_path(path, path_item)

    # STEP 3: Update __init__.py files
    init_generator = InitGenerator(template_dir)
    init_generator.update_endpoint_init_files(output_root)
    init_generator.generate_parent_init_files(output_root)

    print("\n✅ Generation complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Generate SDK routes from OpenAPI spec",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all available paths in the OpenAPI spec",
    )

    parser.add_argument(
        "--path",
        "-p",
        action="append",
        dest="paths",
        help="Generate specific path(s) only (can be specified multiple times)",
    )

    parser.add_argument(
        "--openapi",
        default=Path(__file__).parent / "openapi.json",
        type=Path,
        help="Path to OpenAPI spec (default: openapi.json)",
    )

    args = parser.parse_args()

    openapi_path = args.openapi
    if not openapi_path.exists():
        print(f"Error: OpenAPI spec not found at {openapi_path}")
        return 1

    if args.list:
        list_paths(openapi_path)
        return 0

    output_root = Path(__file__).parent / "generated_routes"

    if args.paths:
        generate_specific_paths(openapi_path, output_root, args.paths)
    else:
        generate_all_routes()

    return 0


if __name__ == "__main__":
    exit(main())
