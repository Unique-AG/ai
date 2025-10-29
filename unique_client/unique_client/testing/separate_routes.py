import json
from pathlib import Path
from typing import Any

import jsonref
from datamodel_code_generator import DataModelType, InputFileType, generate


def generate_model_content(
    schema: dict,
    title: str,
    output_model_type: DataModelType = DataModelType.PydanticV2BaseModel,
) -> str:
    """Generate model content as string instead of writing to file."""
    # Fully dereference jsonref objects
    schema = jsonref.JsonRef.replace_refs(schema)

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
        no_alias=True,
    )

    # Read the generated content
    with open(temp_path, "r") as f:
        content = f.read()

    # Clean up temp file
    temp_path.unlink()

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
    """Convert an OpenAPI path to a folder path, removing curly braces from path params."""
    segments = [seg.strip("{}") for seg in path.strip("/").split("/")]
    return Path(*segments)


def generate_consolidated_endpoint_models():
    """Generate all models for each endpoint in a single file."""
    openapi_path = (
        Path(__file__).parent / "openapi_generator" / "openapi-no-examples.json"
    )
    output_root = Path("generated_routes")

    with openapi_path.open("r") as f:
        openapi: dict[str, Any] = jsonref.load(f)

    for path, methods in openapi.get("paths", {}).items():
        for method, details in methods.items():
            route_dir = output_root / path_to_folder(path) / method.lower()
            models_file = route_dir / "models.py"

            all_models = []
            print(f"Generating models for {method.upper()} {path}")

            # Generate PathParams (always present)
            path_params = [
                p for p in details.get("parameters", []) if p.get("in") == "path"
            ]
            if path_params:
                try:
                    content = generate_model_content(path_params, "PathParams")
                    class_def = extract_class_definitions(content)
                    all_models.append(
                        class_def
                        if class_def.strip()
                        else "class PathParams(BaseModel):\n    pass"
                    )
                except Exception:
                    all_models.append("class PathParams(BaseModel):\n    pass")
            else:
                all_models.append("class PathParams(BaseModel):\n    pass")

            # Generate Request models (generate all, let ruff deduplicate)
            request_generated = False
            for content_details in (
                details.get("requestBody", {}).get("content", {}).values()
            ):
                if request_schema := content_details.get("schema"):
                    try:
                        content = generate_model_content(request_schema, "Request")
                        if class_def := extract_class_definitions(content).strip():
                            all_models.append(class_def)
                            request_generated = True
                    except Exception:
                        pass

            if not request_generated:
                all_models.append("class Request(BaseModel):\n    pass")

            # Generate Response models (generate all, let ruff deduplicate)
            success_responses = [
                code for code in details.get("responses", {}) if code.startswith("2")
            ]
            response_generated = False

            for status_code, response in details.get("responses", {}).items():
                for content_details in response.get("content", {}).values():
                    if response_schema := content_details.get("schema"):
                        try:
                            title = (
                                "Response"
                                if status_code.startswith("2")
                                and len(success_responses) == 1
                                else f"Response{status_code}"
                            )
                            content = generate_model_content(response_schema, title)
                            if class_def := extract_class_definitions(content).strip():
                                all_models.append(class_def)
                                response_generated = True
                        except Exception:
                            pass

            if not response_generated:
                all_models.append("class Response(BaseModel):\n    pass")

            # Write the file (let ruff clean up imports and duplicates)
            models_file.parent.mkdir(parents=True, exist_ok=True)

            with open(models_file, "w") as f:
                f.write(f"# Generated models for {method.upper()} {path}\n")
                f.write("from __future__ import annotations\n\n")
                # Add all possible imports - let ruff remove unused ones
                f.write("from typing import Any, Dict, List, Optional, Union\n")
                f.write("from pydantic import BaseModel, Field\n")
                f.write("from enum import Enum\n")
                f.write("from datetime import datetime\n\n\n")

                for i, model in enumerate(all_models):
                    if i > 0:
                        f.write("\n\n")
                    f.write(model)

            print(f"✅ Created models: {models_file}")


if __name__ == "__main__":
    generate_consolidated_endpoint_models()
