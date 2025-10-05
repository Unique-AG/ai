import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from datamodel_code_generator import DataModelType, InputFileType, generate
from jinja2 import Environment, FileSystemLoader
from openapi_pydantic import OpenAPI, Operation
from openapi_pydantic.v3.v3_1.parameter import Parameter
from openapi_pydantic.v3.v3_1.reference import Reference
from openapi_pydantic.v3.v3_1.request_body import RequestBody
from openapi_pydantic.v3.v3_1.response import Response

# Type alias for JSON-serializable values
JSONValue = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def generate_model_content(
    schema: Dict[str, Any],
    title: str,
    output_model_type: DataModelType = DataModelType.PydanticV2BaseModel,
) -> str:
    """Generate model content as string instead of writing to file."""
    # Schema is already dereferenced when using openapi_pydantic

    schema_json = json.dumps({"title": title, **schema})

    # Generate to temporary file first
    import tempfile

    from datamodel_code_generator.format import (
        PythonVersion,
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    generate(
        input_=schema_json,
        input_file_type=InputFileType.JsonSchema,
        output=temp_path,
        class_name=title,
        output_model_type=output_model_type,
        target_python_version=PythonVersion.PY_313,
        use_standard_collections=True,
        snake_case_field=True,
        use_union_operator=True,
        use_double_quotes=True,
        allow_population_by_field_name=True,
        no_alias=False,  # Allow aliases for camelCase support
        field_constraints=True,  # Use Field() constraints instead of constr for Pydantic v2
    )

    # Read the generated content
    with open(temp_path, "r") as f:
        content = f.read()

    # Clean up temp file
    temp_path.unlink()

    # Replace alias= with both validation_alias= and serialization_alias= for proper Pydantic v2 behavior
    # validation_alias: accepts both snake_case (field name) AND camelCase for flexibility
    # serialization_alias: outputs camelCase for the API
    import re

    # Replace alias="value" with validation_alias="value", serialization_alias="value"
    # This allows input with either snake_case or camelCase, but always outputs camelCase
    content = re.sub(
        r'alias="([^"]+)"', r'validation_alias="\1", serialization_alias="\1"', content
    )

    return content


def extract_class_definitions(content: str) -> str:
    """Extract only class definitions from generated content, removing imports and header comments."""
    lines = content.split("\n")
    class_lines = []
    in_class = False

    for line in lines:
        # Skip header comments and imports
        if (
            line.startswith("#")
            or line.startswith("from ")
            or line.startswith("import ")
            or line.strip() == ""
            and not in_class
        ):
            continue

        # Check if we're starting a class definition
        if line.startswith("class "):
            in_class = True
            class_lines.append(line)
        elif in_class:
            if line.startswith(" ") or line.strip() == "":
                # Still inside the class
                class_lines.append(line)
            else:
                # End of class, check if this is another class
                if line.startswith("class "):
                    class_lines.append("")  # Add blank line between classes
                    class_lines.append(line)
                else:
                    # Not a class, we're done with this class
                    in_class = False

    return "\n".join(class_lines)


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
    import re

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


def create_simple_model_from_schema(
    schema_dict: Dict[str, Any], class_name: str
) -> Optional[str]:
    """Create a simple Pydantic model from a schema when the full generator fails."""
    if not isinstance(schema_dict, dict) or schema_dict.get("type") != "object":
        return None

    properties = schema_dict.get("properties", {})
    required = set(schema_dict.get("required", []))

    if not properties:
        return None

    lines = [f"class {class_name}(BaseModel):"]

    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue

        # Determine Python type
        field_type = "Any"
        if field_schema.get("type") == "string":
            field_type = "str"
        elif field_schema.get("type") == "integer":
            field_type = "int"
        elif field_schema.get("type") == "number":
            field_type = "float"
        elif field_schema.get("type") == "boolean":
            field_type = "bool"
        elif field_schema.get("type") == "array":
            field_type = "list[Any]"
        elif field_schema.get("type") == "object":
            field_type = "dict[str, Any]"

        # Handle nullable fields
        if field_schema.get("nullable", False):
            field_type = f"{field_type} | None"

        # Create field definition
        field_def = f"    {field_name}: {field_type}"

        # Add default if not required
        if field_name not in required:
            if field_schema.get("nullable", False):
                field_def += " = None"
            else:
                field_def += " = Field(default_factory=dict)"

        lines.append(field_def)

    return "\n".join(lines)


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


def generate_model_from_schema(
    schema_dict: Dict[str, Any], class_name: str, raw_spec: Dict[str, Any]
) -> Optional[str]:
    """Generate a model from a schema with fallback to simple model."""
    try:
        # Resolve all references recursively
        resolved_schema = resolve_refs(schema_dict, raw_spec)
        print(f"    - Resolved schema: {resolved_schema}")

        # Try full model generation first
        if isinstance(resolved_schema, dict):
            content = generate_model_content(resolved_schema, class_name)
            if class_def := extract_class_definitions(content).strip():
                return class_def
    except Exception as e:
        print(f"    - Schema error: {e}")

    # Fallback to simple model
    try:
        if isinstance(schema_dict, dict):
            simple_model = create_simple_model_from_schema(schema_dict, class_name)
            if simple_model:
                return simple_model
    except Exception as e:
        print(f"    - Simple model creation failed: {e}")

    return None


def deduplicate_models(models: List[str]) -> List[str]:
    """Remove duplicate model definitions, keeping the first occurrence."""
    seen_classes = set()
    deduplicated = []

    for model in models:
        # Extract class name from the model definition
        # Look for patterns like "class ClassName" or "class ClassName(BaseModel)"
        class_match = re.match(r"^class\s+(\w+)", model.strip())

        if class_match:
            class_name = class_match.group(1)
            if class_name not in seen_classes:
                seen_classes.add(class_name)
                deduplicated.append(model)
        else:
            # Not a class definition, keep it
            deduplicated.append(model)

    return deduplicated


def generate_consolidated_endpoint_models() -> None:
    """Generate all models for each endpoint in a single file."""
    openapi_path = Path(__file__).parent / "openapi.json"
    output_root = Path(__file__).parent / "generated_routes"

    # Load and parse OpenAPI spec using openapi_pydantic
    with openapi_path.open("r") as f:
        raw_spec = json.load(f)

    openapi = OpenAPI.model_validate(raw_spec)

    if not openapi.paths:
        raise ValueError("No paths found in the OpenAPI specification")

    for path, path_item in openapi.paths.items():
        print(f"\nGenerating models for path: {path}")

        # Get all HTTP methods from the PathItem
        methods: dict[str, Operation] = {}
        if path_item.get:
            methods["get"] = path_item.get
        if path_item.post:
            methods["post"] = path_item.post
        if path_item.put:
            methods["put"] = path_item.put
        if path_item.delete:
            methods["delete"] = path_item.delete
        if path_item.patch:
            methods["patch"] = path_item.patch
        if path_item.head:
            methods["head"] = path_item.head
        if path_item.options:
            methods["options"] = path_item.options
        if path_item.trace:
            methods["trace"] = path_item.trace

        # Setup output directory for this path (not per method)
        route_dir = output_root / path_to_folder(path)
        models_file = route_dir / "models.py"

        all_models = []
        operations_info = []  # Track operation info for API client generation

        # Generate PathParams once for the entire path (shared across all operations)
        # Collect all parameters from path_item level
        all_parameters = []
        if path_item.parameters:
            all_parameters.extend(path_item.parameters)

        # Also check the first operation for any path parameters
        if methods:
            first_operation = next(iter(methods.values()))
            if first_operation.parameters:
                all_parameters.extend(first_operation.parameters)

        # Filter path parameters
        path_params = []
        for p in all_parameters:
            if isinstance(p, Parameter) and p.param_in == "path":
                path_params.append(p.model_dump())
            elif isinstance(p, Reference):
                resolved_param = resolve_reference(p, raw_spec)
                if (
                    resolved_param
                    and isinstance(resolved_param, dict)
                    and resolved_param.get("in") == "path"
                ):
                    path_params.append(resolved_param)

        print(f"  Path params: {len(path_params)}")

        # Generate PathParams model only if there are path parameters
        if path_params:
            try:
                # Convert list of parameters to a schema dict
                path_schema = {
                    "type": "object",
                    "properties": {
                        p["name"]: p.get("schema", {"type": "string"})
                        for p in path_params
                    },
                    "required": [
                        p["name"] for p in path_params if p.get("required", False)
                    ],
                }
                content = generate_model_content(path_schema, "PathParams")
                class_def = extract_class_definitions(content)
                all_models.append(
                    class_def
                    if class_def.strip()
                    else "class PathParams(BaseModel):\n    pass"
                )
            except Exception:
                all_models.append("class PathParams(BaseModel):\n    pass")

        # Now process each operation
        for method, operation in methods.items():
            print(f"  Processing {method.upper()} operation")

            # Use method name prefix for model classes
            method_prefix = method.capitalize()

            # Collect parameters for this operation (for query params)
            operation_parameters = []
            if operation.parameters:
                operation_parameters.extend(operation.parameters)
            if path_item.parameters:
                operation_parameters.extend(path_item.parameters)

            print(f"    - Request body: {operation.requestBody is not None}")
            print(
                f"    - Responses: {len(operation.responses) if operation.responses else 0}"
            )

            # Generate Request models
            request_generated = False
            if operation.requestBody:
                request_body = resolve_reference(operation.requestBody, raw_spec)

                if isinstance(request_body, RequestBody) and request_body.content:
                    for content_details in request_body.content.values():
                        if content_details.media_type_schema:
                            schema_dict = content_details.media_type_schema.model_dump()
                            print(f"    - Request schema: {schema_dict}")

                            model = generate_model_from_schema(
                                schema_dict, f"{method_prefix}Request", raw_spec
                            )
                            if model:
                                all_models.append(model)
                            request_generated = True

            if not request_generated:
                all_models.append(f"class {method_prefix}Request(BaseModel):\n    pass")

            # Generate QueryParams models (for query string parameters)
            query_params = []
            for p in operation_parameters:
                if isinstance(p, Parameter) and p.param_in == "query":
                    query_params.append(p.model_dump())
                elif isinstance(p, Reference):
                    resolved_param = resolve_reference(p, raw_spec)
                    if (
                        resolved_param
                        and isinstance(resolved_param, dict)
                        and resolved_param.get("in") == "query"
                    ):
                        query_params.append(resolved_param)

            if query_params:
                try:
                    # Convert list of parameters to a schema dict
                    query_schema = {
                        "type": "object",
                        "properties": {
                            p["name"]: p.get("schema", {"type": "string"})
                            for p in query_params
                        },
                        "required": [
                            p["name"] for p in query_params if p.get("required", False)
                        ],
                    }
                    content = generate_model_content(
                        query_schema, f"{method_prefix}QueryParams"
                    )
                    class_def = extract_class_definitions(content)
                    all_models.append(
                        class_def
                        if class_def.strip()
                        else f"class {method_prefix}QueryParams(BaseModel):\n    pass"
                    )
                except Exception:
                    all_models.append(
                        f"class {method_prefix}QueryParams(BaseModel):\n    pass"
                    )

            # Generate Response models
            success_responses = []
            if operation.responses:
                success_responses = [
                    code for code in operation.responses.keys() if code.startswith("2")
                ]

            print(f"    - Success responses: {success_responses}")
            response_generated = False

            # Use first success response code for API client
            success_code = success_responses[0] if success_responses else "200"

            if operation.responses:
                for status_code, response in operation.responses.items():
                    response_obj = resolve_reference(response, raw_spec)

                    # Handle both Pydantic Response objects and resolved dicts
                    if isinstance(response_obj, Response) and response_obj.content:
                        # Direct Response object from openapi_pydantic
                        for content_details in response_obj.content.values():
                            if content_details.media_type_schema:
                                # Always include status code for clarity
                                title = f"{method_prefix}Response{status_code}"
                                schema_dict = (
                                    content_details.media_type_schema.model_dump()
                                )

                                model = generate_model_from_schema(
                                    schema_dict, title, raw_spec
                                )
                                if model:
                                    all_models.append(model)
                                    response_generated = True
                    elif (
                        response_obj
                        and isinstance(response_obj, dict)
                        and "content" in response_obj
                    ):
                        # Resolved reference as dictionary
                        for media_type, content_data in response_obj["content"].items():
                            if "schema" in content_data:
                                # Always include status code for clarity
                                title = f"{method_prefix}Response{status_code}"
                                schema_dict = content_data["schema"]

                                model = generate_model_from_schema(
                                    schema_dict, title, raw_spec
                                )
                                if model:
                                    all_models.append(model)
                                response_generated = True

            if not response_generated and success_responses:
                # Use first success status code as fallback
                first_success = success_responses[0]
                all_models.append(
                    f"class {method_prefix}Response{first_success}(BaseModel):\n    pass"
                )

            # Only collect operation info if we have success responses
            if success_responses:
                # Check if this operation has query params
                has_query_params = any(
                    (isinstance(p, Parameter) and p.param_in == "query")
                    or (
                        isinstance(p, Reference)
                        and (resolved := resolve_reference(p, raw_spec))
                        and isinstance(resolved, dict)
                        and resolved.get("in") == "query"
                    )
                    for p in operation_parameters
                )

                # Collect operation info for API client generation
                # Capitalize operation name (e.g., deleteFolder -> DeleteFolder)
                operation_name = (
                    operation.operationId
                    or f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
                )
                operation_name = (
                    operation_name[0].upper() + operation_name[1:]
                    if operation_name
                    else operation_name
                )

                operations_info.append(
                    {
                        "method": method,
                        "method_prefix": method_prefix,
                        "name": operation_name,
                        "success_code": success_code,
                        "has_query_params": has_query_params,
                    }
                )

        # Write the file once for all operations in this path
        models_file.parent.mkdir(parents=True, exist_ok=True)

        # Deduplicate models before rendering
        deduplicated_models = deduplicate_models(all_models)

        # Prepare template context
        template_path = path.replace("{", "$").replace("}", "")
        param_examples = (
            ", ".join([f'{p["name"]}="value"' for p in path_params])
            if path_params
            else ""
        )

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent
        env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )
        template = env.get_template("model_template.jinja2")

        # Render template
        rendered = template.render(
            path=path,
            template_path=template_path,
            has_path_params=bool(path_params),
            param_examples=param_examples,
            models=deduplicated_models,
        )

        # Write to file
        with open(models_file, "w") as f:
            f.write(rendered)

        print(f"✅ Created models: {models_file}")

        # Generate API client file
        api_file = route_dir / "path_operation.py"
        api_template = env.get_template("api_template.jinja2")

        # Convert folder name to CamelCase for class name
        import humps

        folder_name = route_dir.name
        # Sanitize folder name: replace special characters with descriptive names
        sanitized_name = (
            folder_name.replace("*", "Wildcard").replace("{", "").replace("}", "")
        )
        class_name = humps.pascalize(sanitized_name) if sanitized_name else "Operation"

        # Convert path to use snake_case parameter names for Python code
        python_path = convert_path_to_snake_case(path)

        api_rendered = api_template.render(
            path=python_path,  # Use snake_case path for Python code
            has_path_params=bool(path_params),
            operations=operations_info,
            class_name=class_name,
        )

        with open(api_file, "w") as f:
            f.write(api_rendered)

        print(f"✅ Created API client: {api_file}")

        # Create __init__.py to export operations and subdirectories
        init_file = route_dir / "__init__.py"

        # Check for subdirectories with __init__.py files
        subdirs = []
        for item in route_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                subdirs.append(item.name)

        subdirs.sort()  # Consistent ordering

        # Extract operation names from operations_info
        operation_names = [op["name"] for op in operations_info]

        # Use Jinja2 template for init file
        endpoint_init_template = env.get_template("endpoint_init_template.jinja2")
        exports = operation_names + subdirs

        init_rendered = endpoint_init_template.render(
            operations=operation_names,
            subdirs=subdirs,
            exports=exports,
        )

        with open(init_file, "w") as f:
            f.write(init_rendered)

        print(f"✅ Created __init__.py: {init_file}")


def update_endpoint_init_files(output_root: Path) -> None:
    """Update endpoint-level __init__.py files to include subdirectories.

    This is a post-processing step that runs after all endpoints are generated,
    ensuring that each endpoint's __init__.py exposes both operations
    and any subdirectories (for nested routes).
    """
    print("\n🔧 Updating endpoint __init__.py files with subdirectories...")

    # Setup Jinja2 environment
    template_dir = Path(__file__).parent
    env = Environment(
        loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
    )
    endpoint_init_template = env.get_template("endpoint_init_template.jinja2")

    # Find all directories with path_operation.py (these are endpoints)
    for root, dirs, files in os.walk(output_root):
        if "path_operation.py" not in files:
            continue

        root_path = Path(root)
        init_file = root_path / "__init__.py"
        path_operation_file = root_path / "path_operation.py"

        if not init_file.exists() or not path_operation_file.exists():
            continue

        # Read path_operation.py to extract operation names
        with open(path_operation_file, "r") as f:
            path_op_content = f.read()

        # Extract operation names (variables assigned with build_requestor)
        # Pattern: operation_name = build_requestor(...)
        operation_names = re.findall(
            r"^(\w+)\s*=\s*build_requestor\(", path_op_content, re.MULTILINE
        )

        if not operation_names:
            continue

        # Find subdirectories with __init__.py
        subdirs = []
        for item in root_path.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                subdirs.append(item.name)

        subdirs.sort()

        # Regenerate the __init__.py with operations and subdirectories using template
        exports = operation_names + subdirs
        init_rendered = endpoint_init_template.render(
            operations=operation_names,
            subdirs=subdirs,
            exports=exports,
        )

        with open(init_file, "w") as f:
            f.write(init_rendered)

        if subdirs or operation_names:
            print(
                f"✅ Updated {init_file.relative_to(output_root)} with ops: {operation_names}, subdirs: {subdirs}"
            )


def generate_parent_init_files(output_root: Path) -> None:
    """Generate __init__.py files for all parent directories in the route tree.

    This creates __init__.py files that expose submodules, making imports like
    'import unique_toolkit.generated.generated_routes.public as client' work.
    """
    print("\n🔧 Generating parent __init__.py files...")

    # Setup Jinja2 environment
    template_dir = Path(__file__).parent
    env = Environment(
        loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
    )
    parent_init_template = env.get_template("parent_init_template.jinja2")

    # Collect all directories that need __init__.py files
    dirs_to_process = set()

    # Walk through all directories in the output_root
    for root, dirs, files in os.walk(output_root):
        root_path = Path(root)

        # Skip if this is a leaf directory (has path_operation.py)
        if "path_operation.py" in files:
            continue

        # Check if this directory has subdirectories with __init__.py
        has_python_subdirs = False
        for subdir in dirs:
            subdir_path = root_path / subdir
            if (subdir_path / "__init__.py").exists():
                has_python_subdirs = True
                break

        if has_python_subdirs:
            dirs_to_process.add(root_path)

    # Generate __init__.py for each directory
    for dir_path in sorted(dirs_to_process):
        # Get immediate subdirectories that have __init__.py
        subdirs = []
        for item in dir_path.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                subdirs.append(item.name)

        if subdirs:
            init_file = dir_path / "__init__.py"

            # Sort subdirs for consistent output
            subdirs.sort()

            # Render template
            init_rendered = parent_init_template.render(subdirs=subdirs)

            with open(init_file, "w") as f:
                f.write(init_rendered)

            print(
                f"✅ Created parent __init__.py: {init_file.relative_to(output_root)}"
            )


if __name__ == "__main__":
    output_root = Path(__file__).parent / "generated_routes"
    generate_consolidated_endpoint_models()
    update_endpoint_init_files(output_root)  # Update endpoints with subdirectories
    generate_parent_init_files(output_root)  # Generate parent directory inits
