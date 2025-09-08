# %%

import json
from pathlib import Path
from typing import Any

import jsonref
from datamodel_code_generator import DataModelType, InputFileType, generate


def normalize_path(path: str) -> str:
    return (
        path.strip("/")
        .replace("/", "_")
        .replace("{", "")
        .replace("}", "")
        .replace("-", "_")
    )


def patch_missing_refs(schema: dict) -> dict:
    """Replace unresolved $refs with empty placeholder objects."""
    if isinstance(schema, dict):
        if "$ref" in schema and not schema["$ref"].startswith("#/components/schemas/"):
            # Keep non-component $refs (e.g. file URLs)
            return schema
        if "$ref" in schema:
            schema["type"] = "object"
            schema.pop("$ref")
        return {k: patch_missing_refs(v) for k, v in schema.items()}
    elif isinstance(schema, list):
        return [patch_missing_refs(item) for item in schema]
    return schema


def generate_model_content(
    schema: dict,
    title: str,
    output_model_type: DataModelType = DataModelType.PydanticBaseModel,
) -> str:
    """Generate model content as string instead of writing to file."""
    # Fully dereference jsonref objects
    schema = jsonref.JsonRef.replace_refs(schema)

    schema_json = json.dumps({"title": title, **schema})

    # Generate to temporary file first
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    generate(
        input_=schema_json,
        input_file_type=InputFileType.JsonSchema,
        output=temp_path,
        class_name=title,
        output_model_type=output_model_type,
    )

    # Read the generated content
    with open(temp_path, "r") as f:
        content = f.read()

    # Clean up temp file
    temp_path.unlink()

    return content


def generate_models_to_file(
    schema: dict,
    title: str,
    output_file: Path,
    output_model_type: DataModelType = DataModelType.PydanticBaseModel,
):
    """Legacy function - generates single model to file."""
    content = generate_model_content(schema, title, output_model_type)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write(content)


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


def to_camel_case(s: str) -> str:
    """Convert a string to CamelCase."""
    return "".join(word.capitalize() for word in s.replace("-", "_").split("_"))


def path_to_folder(path: str) -> Path:
    """Convert an OpenAPI path to a folder path, removing curly braces from path params."""
    segments = [seg.strip("{}") for seg in path.strip("/").split("/")]
    return Path(*segments)


def generate_consolidated_endpoint_models():
    """Generate all models for each endpoint in a single file."""
    openapi_path = Path(__file__).parent / "openapi.json"
    output_root = Path("generated_routes")

    with open(openapi_path) as f:
        openapi: dict[str, Any] = jsonref.load(f)

    for path, methods in openapi.get("paths", {}).items():
        for method, details in methods.items():
            route_name = f"{method.lower()}_{normalize_path(path)}"
            route_dir = output_root / path_to_folder(path) / method.lower()
            models_file = route_dir / "models.py"

            # Collect all model content for this endpoint
            all_models = []
            imports_needed = set()

            print(f"Generating models for {method.upper()} {path}")

            # Path parameters as Pydantic model
            path_params = [
                p for p in details.get("parameters", []) if p.get("in") == "path"
            ]
            if path_params:
                try:
                    content = generate_model_content(
                        path_params,
                        title="PathParams",
                        output_model_type=DataModelType.PydanticBaseModel,
                    )
                    class_def = extract_class_definitions(content)
                    if class_def.strip():
                        all_models.append(class_def)
                        imports_needed.update(["BaseModel", "Field"])
                except Exception as e:
                    print(f"Error generating path params for {route_name}: {e}")

            # Request schema as Pydantic model
            request_schema = next(
                iter(details.get("requestBody", {}).get("content", {}).values()), {}
            ).get("schema")

            if request_schema:
                try:
                    content = generate_model_content(
                        request_schema,
                        title="Request",
                        output_model_type=DataModelType.PydanticBaseModel,
                    )
                    class_def = extract_class_definitions(content)
                    if class_def.strip():
                        all_models.append(class_def)
                        imports_needed.update(["BaseModel", "Field"])
                except Exception as e:
                    print(f"Error generating request model for {route_name}: {e}")

            # Response schemas as Pydantic models
            success_responses = [
                code
                for code in details.get("responses", {}).keys()
                if code.startswith("2")
            ]
            for status_code, response in details.get("responses", {}).items():
                response_schema = next(
                    iter(response.get("content", {}).values()), {}
                ).get("schema")
                if response_schema:
                    try:
                        # Use simple "Response" for successful responses, or include status for others
                        if status_code.startswith("2") and len(success_responses) == 1:
                            title = "Response"
                        else:
                            title = f"Response{status_code}"

                        content = generate_model_content(
                            response_schema,
                            title=title,
                            output_model_type=DataModelType.PydanticBaseModel,
                        )
                        class_def = extract_class_definitions(content)
                        if class_def.strip():
                            all_models.append(class_def)
                            imports_needed.update(["BaseModel", "Field"])
                    except Exception as e:
                        print(f"Error generating response model for {route_name}: {e}")

            # Only create the file if we have models to write
            if all_models:
                # Create the consolidated file
                models_file.parent.mkdir(parents=True, exist_ok=True)

                with open(models_file, "w") as f:
                    # Write header
                    f.write("# Generated models for endpoint\n")
                    f.write(f"# {method.upper()} {path}\n\n")

                    # Write imports
                    f.write("from __future__ import annotations\n\n")

                    # Determine what to import based on what's needed
                    typing_imports = []
                    pydantic_imports = []

                    if "BaseModel" in imports_needed:
                        pydantic_imports.append("BaseModel")
                    if "Field" in imports_needed:
                        pydantic_imports.append("Field")

                    # We might need these for generated models
                    typing_imports.extend(["Any", "Dict", "List", "Optional", "Union"])

                    if typing_imports:
                        f.write(
                            f"from typing import {', '.join(sorted(typing_imports))}\n"
                        )
                    if pydantic_imports:
                        f.write(
                            f"from pydantic import {', '.join(sorted(pydantic_imports))}\n"
                        )

                    # Check if we need additional imports by scanning the model content
                    all_content = "\n".join(all_models)
                    if "Enum" in all_content and "Enum" not in typing_imports:
                        f.write("from enum import Enum\n")
                    if "datetime" in all_content:
                        f.write("from datetime import datetime\n")

                    f.write("\n\n")

                    # Write all models
                    for i, model_content in enumerate(all_models):
                        if i > 0:
                            f.write("\n\n")
                        f.write(model_content)

                print(f"✅ Created consolidated models: {models_file}")


generate_consolidated_endpoint_models()

# %%
