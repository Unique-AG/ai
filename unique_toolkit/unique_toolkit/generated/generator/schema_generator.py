"""Schema and model generation from OpenAPI schemas."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from datamodel_code_generator import DataModelType, InputFileType, generate
from datamodel_code_generator.format import PythonVersion

from .utils import resolve_refs


def generate_model_content(
    schema: Dict[str, Any],
    title: str,
    output_model_type: DataModelType = DataModelType.PydanticV2BaseModel,
) -> str:
    """Generate model content as string instead of writing to file."""
    schema_json = json.dumps({"title": title, **schema})

    # Generate to temporary file first
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
    import re

    content = re.sub(
        r'alias="([^"]+)"', r'validation_alias="\1", serialization_alias="\1"', content
    )

    return content


def extract_class_definitions(content: str, target_class: str = None) -> str:
    """Extract class definitions from generated content.

    Args:
        content: Generated Python code content
        target_class: If specified, extract only this class and put it first

    Returns:
        Extracted class definitions
    """
    lines = content.split("\n")
    in_class = False
    current_class_lines = []
    current_class_name = None
    all_classes = {}  # class_name -> lines

    for line in lines:
        # Skip header comments and imports
        if (
            line.startswith("#")
            or line.startswith("from ")
            or line.startswith("import ")
            or (line.strip() == "" and not in_class)
        ):
            continue

        # Check if we're starting a class definition
        if line.startswith("class "):
            # Save previous class if any
            if current_class_name and current_class_lines:
                all_classes[current_class_name] = current_class_lines[:]

            # Extract class name
            import re

            match = re.match(r"class\s+(\w+)", line)
            current_class_name = match.group(1) if match else None
            current_class_lines = [line]
            in_class = True
        elif in_class:
            if line.startswith(" ") or line.strip() == "":
                # Still inside the class
                current_class_lines.append(line)
            else:
                # End of class
                if current_class_name and current_class_lines:
                    all_classes[current_class_name] = current_class_lines[:]
                current_class_lines = []
                current_class_name = None
                in_class = False

                # Check if this line starts another class
                if line.startswith("class "):
                    match = re.match(r"class\s+(\w+)", line)
                    current_class_name = match.group(1) if match else None
                    current_class_lines = [line]
                    in_class = True

    # Save last class
    if current_class_name and current_class_lines:
        all_classes[current_class_name] = current_class_lines[:]

    # Build output - target class first if specified, then rest
    output_lines = []
    if target_class and target_class in all_classes:
        output_lines.extend(all_classes[target_class])
        output_lines.append("")
        for class_name, lines in all_classes.items():
            if class_name != target_class:
                output_lines.append("")
                output_lines.extend(lines)
    else:
        # No target or target not found, return all classes
        for class_name, lines in all_classes.items():
            if output_lines:
                output_lines.append("")
            output_lines.extend(lines)

    return "\n".join(output_lines)


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


def generate_model_from_schema(
    schema_dict: Dict[str, Any], class_name: str, raw_spec: Dict[str, Any]
) -> Optional[str]:
    """Generate a model from a schema with fallback to simple model."""
    try:
        # Resolve all references recursively
        resolved_schema = resolve_refs(schema_dict, raw_spec)

        # Try full model generation first
        if isinstance(resolved_schema, dict):
            content = generate_model_content(resolved_schema, class_name)
            if class_def := extract_class_definitions(content, class_name).strip():
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
