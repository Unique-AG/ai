#!/usr/bin/env python3
"""
Model Generation Utilities

This module contains all the low-level functions for creating individual
Pydantic models and processing generated code. These utilities are used
by the functional generator for orchestrating the overall generation process.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Union

from datamodel_code_generator import DataModelType, InputFileType, generate
from openapi_pydantic.v3.v3_0 import Schema


def get_datamodel_config() -> dict[str, Any]:
    """Get standard datamodel-codegen configuration for Pydantic v2."""
    return {
        "input_file_type": InputFileType.JsonSchema,
        "snake_case_field": True,
        "use_union_operator": True,
        "field_constraints": True,
        "validation": True,
        "use_standard_collections": True,
        "use_annotated": True,
        "use_generic_container_types": True,
        "use_schema_description": True,
        "use_subclass_enum": True,
        "strict_nullable": True,
        "use_double_quotes": True,
        "collapse_root_models": True,
        "use_one_literal_as_default": True,
    }


def schema_to_dict(schema: Union[Schema, dict[str, Any]]) -> dict[str, Any]:
    """Convert Schema object to dictionary."""
    if isinstance(schema, Schema):
        return schema.model_dump(exclude_none=True, by_alias=True)
    elif isinstance(schema, dict):
        return schema
    else:
        return {"type": "object", "additionalProperties": True}


def create_schema_dict(
    schema: Union[Schema, dict[str, Any]], model_name: str
) -> dict[str, Any]:
    """Create JSON schema dictionary."""
    schema_dict = schema_to_dict(schema)
    return {"title": model_name, **schema_dict}


def generate_model_to_temp_file(
    schema: dict[str, Any], model_name: str, model_type: DataModelType
) -> Path | None:
    """Generate a model to temporary file using datamodel-codegen."""
    try:
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()

        schema_json = json.dumps(schema)
        config = get_datamodel_config()
        generate(
            input_=schema_json,
            output=temp_path,
            class_name=model_name,
            output_model_type=model_type,
            **config,
        )

        return temp_path
    except Exception as e:
        print(f"❌ Error generating model {model_name}: {e}")
        return None


def process_class_definition(class_lines: list[str]) -> list[str]:
    """Process a class definition, handling __root__ fields."""
    if not class_lines:
        return []

    # Check if this class has a __root__ field
    has_root = any("__root__:" in line for line in class_lines)

    if has_root:
        # Convert __root__ model to a simpler pass model for now
        class_header = class_lines[0]  # class ClassName(BaseModel):
        return [
            class_header,
            "    pass",
            "",
            "    class Config:",
            "        extra = Extra.allow",
            "",
        ]
    else:
        # Return the class as-is
        return class_lines


def read_temp_file_content(temp_file: Path) -> list[str]:
    """Read and extract class definitions from temporary file."""
    try:
        with open(temp_file, "r") as f:
            content = f.read()

        lines = content.split("\n")
        result_lines = []
        capturing = False
        current_class_lines = []

        for line in lines:
            if line.startswith("class ") and (
                "BaseModel" in line or "TypedDict" in line
            ):
                # Process previous class if we have one
                if current_class_lines:
                    processed_class = process_class_definition(current_class_lines)
                    result_lines.extend(processed_class)
                    current_class_lines = []

                capturing = True
                current_class_lines.append(line)
            elif capturing:
                if line.startswith(" ") or line.strip() == "":
                    current_class_lines.append(line)
                elif line.strip() and not line.startswith(" "):
                    if line.startswith("class "):
                        # Process the previous class
                        if current_class_lines:
                            processed_class = process_class_definition(
                                current_class_lines
                            )
                            result_lines.extend(processed_class)
                            current_class_lines = []
                        current_class_lines.append(line)
                    else:
                        # End of class definitions
                        if current_class_lines:
                            processed_class = process_class_definition(
                                current_class_lines
                            )
                            result_lines.extend(processed_class)
                            current_class_lines = []
                        break

        # Process final class if we have one
        if current_class_lines:
            processed_class = process_class_definition(current_class_lines)
            result_lines.extend(processed_class)

        result_lines.append("")
        return result_lines
    except Exception as e:
        print(f"❌ Error reading temp file {temp_file}: {e}")
        return [f"# Error reading temp file: {e}", ""]


def create_request_model(
    operation_request_body, base_name: str, temp_files: list[Path]
) -> tuple[str | None, list[str]]:
    """Create a request model from operation request body."""
    if not (
        operation_request_body
        and hasattr(operation_request_body, "content")
        and operation_request_body.content
    ):
        return None, []

    model_name = f"{base_name}Payload"
    content = operation_request_body.content
    media_type = next(iter(content.values()))

    if not (media_type and media_type.media_type_schema):
        return None, []

    temp_file = generate_model_to_temp_file(
        create_schema_dict(media_type.media_type_schema, model_name),
        model_name,
        DataModelType.PydanticBaseModel,
    )

    if not temp_file:
        return None, []

    temp_files.append(temp_file)
    file_content = read_temp_file_content(temp_file)
    return model_name, file_content


def create_success_model(
    operation_responses, base_name: str, temp_files: list[Path]
) -> tuple[str | None, list[str], str | None]:
    """Create a success response model from operation responses."""
    if not operation_responses:
        return None, [], None

    # Find the first successful response (2xx status code)
    for status_code, response in operation_responses.items():
        if (
            status_code.startswith("2")
            and hasattr(response, "content")
            and response.content
        ):
            model_name = f"{base_name}Success"
            content = response.content
            media_type = next(iter(content.values()))

            if not (media_type and media_type.media_type_schema):
                return None, [], status_code

            temp_file = generate_model_to_temp_file(
                create_schema_dict(media_type.media_type_schema, model_name),
                model_name,
                DataModelType.PydanticBaseModel,
            )

            if not temp_file:
                return None, [], status_code

            temp_files.append(temp_file)
            file_content = read_temp_file_content(temp_file)
            return model_name, file_content, status_code

    return None, [], None


def create_empty_request_model(
    base_name: str, method: str, path: str
) -> tuple[str, list[str]]:
    """Create an empty request model when no request body is defined."""
    model_name = f"{base_name}Request"
    file_content = [
        f"class {model_name}(BaseModel):",
        f'    """Request model for {method.upper()} {path}"""',
        "    pass",
        "",
    ]
    return model_name, file_content


def create_empty_success_model(
    base_name: str, method: str, path: str
) -> tuple[str, list[str]]:
    """Create an empty success model when no success response is defined."""
    model_name = f"{base_name}Response"
    file_content = [
        f"class {model_name}(BaseModel):",
        f'    """Response model for {method.upper()} {path}"""',
        "    pass",
        "",
    ]
    return model_name, file_content


def create_path_params_typeddict(
    path_params, base_name: str, method: str, path: str, naming_strategy
) -> tuple[str, list[str]]:
    """Create TypedDict for path parameters."""
    if not path_params:
        return "NoPathParams", []

    path_params_type = f"{base_name}PathParams"
    file_content = [
        f"class {path_params_type}(TypedDict):",
        f'    """Path parameters for {method.upper()} {path}"""',
    ]

    for param in path_params:
        param_type = naming_strategy.get_python_type_hint(param.param_schema)
        file_content.append(f"    {param.name}: {param_type}")

    file_content.append("")
    return path_params_type, file_content


def cleanup_temp_files(temp_files: list[Path]) -> None:
    """Clean up temporary files."""
    for temp_file in temp_files:
        try:
            temp_file.unlink()
        except OSError:
            pass
