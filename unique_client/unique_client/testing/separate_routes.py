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


def generate_models_to_file(
    schema: dict,
    title: str,
    output_file: Path,
    output_model_type: DataModelType = DataModelType.PydanticBaseModel,
):
    # Fully dereference jsonref objects
    schema = jsonref.JsonRef.replace_refs(schema)

    schema_json = json.dumps({"title": title, **schema})
    output_file.parent.mkdir(parents=True, exist_ok=True)

    generate(
        input_=schema_json,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        class_name=title,
        output_model_type=output_model_type,
    )


def to_camel_case(s: str) -> str:
    """Convert a string to CamelCase."""
    return "".join(word.capitalize() for word in s.replace("-", "_").split("_"))


def generate_path_params_typed_dict(params, title, output_file):
    """Generate a TypedDict for path parameters."""
    fields = []
    type_map = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
    }
    for param in params:
        if param.get("in") == "path":
            name = param["name"]
            typ = param.get("schema", {}).get("type", "string")
            py_type = type_map.get(typ, "Any")
            fields.append(f"    {name}: {py_type}")
    if fields:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        class_name = to_camel_case(title)
        with open(output_file, "w") as f:
            f.write("from typing import TypedDict\n\n")
            f.write(f"class {class_name}(TypedDict):\n")
            for field in fields:
                f.write(field + "\n")


def path_to_folder(path: str) -> Path:
    """Convert an OpenAPI path to a folder path, removing curly braces from path params."""
    segments = [seg.strip("{}") for seg in path.strip("/").split("/")]
    return Path(*segments)


# %%
openapi_path = Path("openapi.json")
output_root = Path("generated_routes")

with open(openapi_path) as f:
    openapi: dict[str, Any] = jsonref.load(f)

for path, methods in openapi.get("paths", {}).items():
    for method, details in methods.items():
        route_name = f"{method.lower()}_{normalize_path(path)}"
        route_dir = output_root / path_to_folder(path) / method.lower()

        # Path parameters as TypedDict
        path_params = [
            p for p in details.get("parameters", []) if p.get("in") == "path"
        ]
        if path_params:
            generate_path_params_typed_dict(
                path_params,
                title=f"{route_name}_PathParams",
                output_file=route_dir / "path_params.py",
            )

        # Request schema as TypedDict
        request_schema = next(
            iter(details.get("requestBody", {}).get("content", {}).values()), {}
        ).get("schema")

        if request_schema:
            try:
                generate_models_to_file(
                    request_schema,
                    title=f"{route_name}_Request",
                    output_file=route_dir / "request_model.py",
                    output_model_type=DataModelType.TypingTypedDict,
                )
            except Exception as e:
                print(f"Error generating request model for {route_name}: {e}")

        # Response schemas as Pydantic models
        for status_code, response in details.get("responses", {}).items():
            response_schema = next(iter(response.get("content", {}).values()), {}).get(
                "schema"
            )
            if response_schema:
                generate_models_to_file(
                    response_schema,
                    title=f"{route_name}_Response_{status_code}",
                    output_file=route_dir / f"response_{status_code}_model.py",
                    output_model_type=DataModelType.PydanticBaseModel,
                )


# %%
