"""Process individual OpenAPI paths and generate route files."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import humps
from openapi_pydantic import Operation
from openapi_pydantic.v3.v3_1.parameter import Parameter
from openapi_pydantic.v3.v3_1.path_item import PathItem
from openapi_pydantic.v3.v3_1.reference import Reference
from openapi_pydantic.v3.v3_1.response import Response

from .schema_generator import generate_model_from_schema
from .template_renderer import TemplateRenderer
from .utils import (
    convert_path_to_snake_case,
    deduplicate_models,
    path_to_folder,
    resolve_reference,
    truncate_path,
)


class PathProcessor:
    """Process individual OpenAPI paths and generate corresponding SDK code."""

    def __init__(self, template_dir: Path, output_root: Path, raw_spec: Dict[str, Any]):
        """Initialize the path processor.

        Args:
            template_dir: Directory containing Jinja2 templates
            output_root: Root directory for generated routes
            raw_spec: Raw OpenAPI specification as dict
        """
        self.renderer = TemplateRenderer(template_dir)
        self.output_root = output_root
        self.raw_spec = raw_spec

    def process_path(self, path: str, path_item: PathItem) -> None:
        """Process a single OpenAPI path and generate all necessary files.

        Args:
            path: OpenAPI path (e.g., "/public/messages")
            path_item: PathItem object from OpenAPI spec
        """
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

        # Setup output directory for this path
        route_dir = self.output_root / path_to_folder(path)
        models_file = route_dir / "models.py"

        all_models = []
        operations_info = []  # Track operation info for API client generation

        # Generate PathParams once for the entire path
        path_params = self._extract_path_params(path_item, methods)
        print(f"  Path params: {len(path_params)}")

        if path_params:
            path_params_model = self._generate_path_params_model(path_params)
            all_models.append(path_params_model)

        # Process each operation
        for method, operation in methods.items():
            print(f"  Processing {method.upper()} operation")
            method_prefix = method.capitalize()

            # Collect parameters for this operation
            operation_parameters = []
            if operation.parameters:
                operation_parameters.extend(operation.parameters)
            if path_item.parameters:
                operation_parameters.extend(path_item.parameters)

            # Generate Request models
            request_model = self._generate_request_model(operation, method_prefix)
            all_models.append(request_model)

            # Generate QueryParams models
            query_params_model = self._generate_query_params_model(
                operation_parameters, method_prefix
            )
            if query_params_model:
                all_models.append(query_params_model)

            # Generate Response models
            response_info, response_models = self._generate_response_models(
                operation, method_prefix
            )
            all_models.extend(response_models)

            # Collect operation info
            operation_info = self._collect_operation_info(
                operation,
                method,
                method_prefix,
                path,
                response_info,
                operation_parameters,
            )
            if operation_info:
                operations_info.append(operation_info)

        # Write models file
        self._write_models_file(models_file, path, path_params, all_models)

        # Generate API client file
        self._write_api_client_file(route_dir, path, path_params, operations_info)

        # Create __init__.py to export operations and subdirectories
        self._write_endpoint_init_file(route_dir, operations_info)

    def _extract_path_params(
        self, path_item: PathItem, methods: dict[str, Operation]
    ) -> List[Dict[str, Any]]:
        """Extract path parameters from path item and operations."""
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
                resolved_param = resolve_reference(p, self.raw_spec)
                if (
                    resolved_param
                    and isinstance(resolved_param, dict)
                    and resolved_param.get("in") == "path"
                ):
                    path_params.append(resolved_param)

        return path_params

    def _generate_path_params_model(self, path_params: List[Dict[str, Any]]) -> str:
        """Generate PathParams model from path parameters."""
        try:
            from .schema_generator import (
                extract_class_definitions,
                generate_model_content,
            )

            path_schema = {
                "type": "object",
                "properties": {
                    p["name"]: p.get("schema", {"type": "string"}) for p in path_params
                },
                "required": [
                    p["name"] for p in path_params if p.get("required", False)
                ],
            }
            content = generate_model_content(path_schema, "PathParams")
            class_def = extract_class_definitions(content)
            return (
                class_def
                if class_def.strip()
                else "class PathParams(BaseModel):\n    pass"
            )
        except Exception:
            return "class PathParams(BaseModel):\n    pass"

    def _generate_request_model(self, operation: Operation, method_prefix: str) -> str:
        """Generate request model for an operation."""
        if operation.requestBody:
            request_body = resolve_reference(operation.requestBody, self.raw_spec)

            if hasattr(request_body, "content") and request_body.content:
                for content_details in request_body.content.values():
                    if content_details.media_type_schema:
                        schema_dict = content_details.media_type_schema.model_dump()

                        model = generate_model_from_schema(
                            schema_dict, f"{method_prefix}Request", self.raw_spec
                        )
                        if model:
                            return model

        return f"class {method_prefix}Request(BaseModel):\n    pass"

    def _generate_query_params_model(
        self, operation_parameters: List[Any], method_prefix: str
    ) -> Optional[str]:
        """Generate QueryParams model if operation has query parameters."""
        query_params = []
        for p in operation_parameters:
            if isinstance(p, Parameter) and p.param_in == "query":
                query_params.append(p.model_dump())
            elif isinstance(p, Reference):
                resolved_param = resolve_reference(p, self.raw_spec)
                if (
                    resolved_param
                    and isinstance(resolved_param, dict)
                    and resolved_param.get("in") == "query"
                ):
                    query_params.append(resolved_param)

        if query_params:
            try:
                from .schema_generator import (
                    extract_class_definitions,
                    generate_model_content,
                )

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
                return (
                    class_def
                    if class_def.strip()
                    else f"class {method_prefix}QueryParams(BaseModel):\n    pass"
                )
            except Exception:
                return f"class {method_prefix}QueryParams(BaseModel):\n    pass"

        return None

    def _generate_response_models(
        self, operation: Operation, method_prefix: str
    ) -> tuple[Dict[str, Any], List[str]]:
        """Generate response models and return metadata.

        Returns:
            Tuple of (response_info_dict, list_of_generated_models)
        """
        generated_models = []
        success_responses = []
        if operation.responses:
            success_responses = [
                code for code in operation.responses.keys() if code.startswith("2")
            ]

        success_code = success_responses[0] if success_responses else "200"

        # Generate descriptive response name from operationId
        base_response_name = ""
        if operation.operationId:
            capitalized = (
                operation.operationId[0].upper() + operation.operationId[1:]
                if operation.operationId
                else ""
            )
            base_response_name = f"{capitalized}Response"
        else:
            base_response_name = f"{method_prefix}Response"

        if operation.responses:
            for status_code, response in operation.responses.items():
                response_obj = resolve_reference(response, self.raw_spec)

                if isinstance(response_obj, Response) and response_obj.content:
                    for content_details in response_obj.content.values():
                        if content_details.media_type_schema:
                            title = (
                                base_response_name
                                if status_code.startswith("2")
                                else f"{base_response_name}{status_code}"
                            )
                            # Resolve reference if needed
                            schema = resolve_reference(
                                content_details.media_type_schema, self.raw_spec
                            )
                            schema_dict = (
                                schema
                                if isinstance(schema, dict)
                                else content_details.media_type_schema.model_dump()
                            )

                            model = generate_model_from_schema(
                                schema_dict, title, self.raw_spec
                            )
                            if model:
                                generated_models.append(model)
                elif (
                    response_obj
                    and isinstance(response_obj, dict)
                    and "content" in response_obj
                ):
                    for media_type, content_data in response_obj["content"].items():
                        if "schema" in content_data:
                            title = (
                                base_response_name
                                if status_code.startswith("2")
                                else f"{base_response_name}{status_code}"
                            )
                            schema_dict = content_data["schema"]

                            model = generate_model_from_schema(
                                schema_dict, title, self.raw_spec
                            )
                            if model:
                                generated_models.append(model)

        # Always ensure we have a response model for success responses
        if success_responses:
            response_model_exists = any(
                base_response_name in model and "class" in model
                for model in generated_models
            )
            if not response_model_exists:
                generated_models.append(
                    f"class {base_response_name}(BaseModel):\n    pass"
                )

        return (
            {
                "success_code": success_code,
                "response_model": base_response_name,
                "has_success_responses": bool(success_responses),
            },
            generated_models,
        )

    def _collect_operation_info(
        self,
        operation: Operation,
        method: str,
        method_prefix: str,
        path: str,
        response_info: Dict[str, Any],
        operation_parameters: List[Any],
    ) -> Optional[Dict[str, Any]]:
        """Collect operation metadata for API client generation."""
        if not response_info["has_success_responses"]:
            return None

        # Check if this operation has query params
        has_query_params = any(
            (isinstance(p, Parameter) and p.param_in == "query")
            or (
                isinstance(p, Reference)
                and (resolved := resolve_reference(p, self.raw_spec))
                and isinstance(resolved, dict)
                and resolved.get("in") == "query"
            )
            for p in operation_parameters
        )

        # Capitalize operation name
        operation_name = (
            operation.operationId
            or f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
        )
        operation_name = (
            operation_name[0].upper() + operation_name[1:]
            if operation_name
            else operation_name
        )

        return {
            "method": method,
            "method_prefix": method_prefix,
            "name": operation_name,
            "success_code": response_info["success_code"],
            "has_query_params": has_query_params,
            "response_model": response_info["response_model"],
        }

    def _write_models_file(
        self,
        models_file: Path,
        path: str,
        path_params: List[Dict[str, Any]],
        all_models: List[str],
    ) -> None:
        """Write the models.py file."""
        models_file.parent.mkdir(parents=True, exist_ok=True)

        # Deduplicate models
        deduplicated_models = deduplicate_models(all_models)

        # Prepare template context
        template_path = path.replace("{", "$").replace("}", "")
        param_examples = (
            ", ".join([f'{p["name"]}="value"' for p in path_params])
            if path_params
            else ""
        )

        # Render template
        rendered = self.renderer.render_models(
            path=path,
            template_path=template_path,
            has_path_params=bool(path_params),
            param_examples=param_examples,
            models=deduplicated_models,
        )

        with open(models_file, "w") as f:
            f.write(rendered)

        print(f"✅ Models: {truncate_path(models_file)}")

    def _write_api_client_file(
        self,
        route_dir: Path,
        path: str,
        path_params: List[Dict[str, Any]],
        operations_info: List[Dict[str, Any]],
    ) -> None:
        """Write the path_operation.py file."""
        api_file = route_dir / "path_operation.py"

        # Convert folder name to CamelCase for class name
        folder_name = route_dir.name
        sanitized_name = (
            folder_name.replace("*", "Wildcard").replace("{", "").replace("}", "")
        )
        class_name = humps.pascalize(sanitized_name) if sanitized_name else "Operation"

        # Convert path to use snake_case parameter names
        python_path = convert_path_to_snake_case(path)

        api_rendered = self.renderer.render_api_client(
            path=python_path,
            python_path=python_path,
            has_path_params=bool(path_params),
            operations=operations_info,
            class_name=class_name,
        )

        with open(api_file, "w") as f:
            f.write(api_rendered)

        print(f"✅ API: {truncate_path(api_file)}")

    def _write_endpoint_init_file(
        self, route_dir: Path, operations_info: List[Dict[str, Any]]
    ) -> None:
        """Write the endpoint __init__.py file."""
        init_file = route_dir / "__init__.py"

        # Check for subdirectories with __init__.py files
        subdirs = []
        for item in route_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                subdirs.append(item.name)

        subdirs.sort()

        # Extract operation names
        operation_names = [op["name"] for op in operations_info]

        # Render template
        exports = operation_names + subdirs
        init_rendered = self.renderer.render_endpoint_init(
            operations=operation_names,
            subdirs=subdirs,
            exports=exports,
        )

        with open(init_file, "w") as f:
            f.write(init_rendered)

        print(f"✅ Init: {truncate_path(init_file)}")
