"""Process individual OpenAPI paths and generate route files."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from openapi_pydantic import Operation
from openapi_pydantic.v3.v3_1.parameter import Parameter
from openapi_pydantic.v3.v3_1.path_item import PathItem
from openapi_pydantic.v3.v3_1.reference import Reference

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
        # Build set of cleaned component schema names
        original_schemas = raw_spec.get("components", {}).get("schemas", {}).keys()
        self.component_schemas = {
            self._clean_schema_name(name) for name in original_schemas
        }

    @staticmethod
    def _clean_schema_name(schema_name: str) -> str:
        """Clean schema name by removing 'Public' prefix and 'Dto' suffix."""
        clean_name = schema_name
        if clean_name.startswith("Public"):
            clean_name = clean_name[6:]  # Remove "Public"
        if clean_name.endswith("Dto"):
            clean_name = clean_name[:-3]  # Remove "Dto"
        return clean_name

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
        operation_file = route_dir / "operation.py"

        all_models = []
        referenced_components = set()  # Track component schemas used in this path
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
            request_model, request_components = self._generate_request_model(
                operation, method_prefix
            )
            if request_components:
                referenced_components.update(request_components)
            if request_model:
                all_models.append(request_model)

            # Generate QueryParams models
            query_params_model = self._generate_query_params_model(
                operation_parameters, method_prefix
            )
            if query_params_model:
                all_models.append(query_params_model)

            # Generate Response models
            response_info, response_models, response_components = (
                self._generate_response_models(operation, method_prefix)
            )
            if response_components:
                referenced_components.update(response_components)
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

        # Write combined operation file (models + API operations)
        self._write_operation_file(
            operation_file,
            path,
            path_params,
            all_models,
            referenced_components,
            operations_info,
        )

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

    def _extract_schema_name_from_ref(
        self, schema_dict: Dict[str, Any]
    ) -> Optional[str]:
        """Extract schema name from $ref if present.

        Args:
            schema_dict: Schema dictionary that might contain a $ref

        Returns:
            Schema name if $ref is present (e.g., 'PublicMessageDto'), None otherwise
        """
        if isinstance(schema_dict, dict) and "$ref" in schema_dict:
            ref = schema_dict["$ref"]
            # Extract the last part of the reference path
            # e.g., "#/components/schemas/PublicMessageDto" -> "PublicMessageDto"
            if "/" in ref:
                return ref.split("/")[-1]
        return None

    def _generate_request_model(
        self, operation: Operation, method_prefix: str
    ) -> tuple[Optional[str], set[str]]:
        """Generate request model for an operation.

        Returns:
            Tuple of (model_string, set_of_component_names)
        """
        referenced_components = set()

        if operation.requestBody:
            request_body = resolve_reference(operation.requestBody, self.raw_spec)

            content = getattr(request_body, "content", None) or (
                request_body.get("content") if isinstance(request_body, dict) else None
            )
            if content:
                for content_details in content.values():
                    media_type_schema = getattr(
                        content_details, "media_type_schema", None
                    ) or (
                        content_details.get("schema")
                        if isinstance(content_details, dict)
                        else None
                    )
                    if media_type_schema:
                        # Extract schema name from $ref BEFORE model_dump() to preserve it
                        actual_schema_name = None
                        if isinstance(media_type_schema, Reference):
                            if hasattr(media_type_schema, "ref"):
                                ref = media_type_schema.ref
                                if "/" in ref:
                                    actual_schema_name = ref.split("/")[-1]

                        # If not extracted yet, try from model_dump
                        if not actual_schema_name:
                            temp_dict = (
                                media_type_schema.model_dump()
                                if hasattr(media_type_schema, "model_dump")
                                else media_type_schema
                            )
                            if isinstance(temp_dict, dict):
                                actual_schema_name = self._extract_schema_name_from_ref(
                                    temp_dict
                                )

                        # Clean the schema name and check if it references a component
                        if actual_schema_name:
                            clean_schema_name = self._clean_schema_name(
                                actual_schema_name
                            )
                            if clean_schema_name in self.component_schemas:
                                referenced_components.add(clean_schema_name)
                                # Create an alias for the API client to use
                                alias = f"{method_prefix}Request = {clean_schema_name}"
                                return (alias, referenced_components)

                        title = actual_schema_name or f"{method_prefix}Request"

                        # Resolve reference and convert to dict
                        schema = resolve_reference(media_type_schema, self.raw_spec)
                        if isinstance(schema, dict):
                            schema_dict = schema
                        elif hasattr(media_type_schema, "model_dump"):
                            schema_dict = media_type_schema.model_dump()
                        else:
                            schema_dict = (
                                media_type_schema
                                if isinstance(media_type_schema, dict)
                                else {}
                            )

                        model = generate_model_from_schema(
                            schema_dict, title, self.raw_spec
                        )
                        if model:
                            return (model, referenced_components)

        return (
            f"class {method_prefix}Request(BaseModel):\n    pass",
            referenced_components,
        )

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
    ) -> tuple[Dict[str, Any], List[str], set[str]]:
        """Generate response models and return metadata.

        Returns:
            Tuple of (response_info_dict, list_of_generated_models, set_of_component_names)
        """
        generated_models = []
        referenced_components = set()
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

                content = getattr(response_obj, "content", None) or (
                    response_obj.get("content")
                    if isinstance(response_obj, dict)
                    else None
                )
                if content:
                    for content_details in content.values():
                        media_type_schema = getattr(
                            content_details, "media_type_schema", None
                        ) or (
                            content_details.get("schema")
                            if isinstance(content_details, dict)
                            else None
                        )
                        if media_type_schema:
                            # Extract schema name from $ref BEFORE model_dump() to preserve it
                            # Check if it's a Reference object first
                            actual_schema_name = None
                            if isinstance(media_type_schema, Reference):
                                # It's a Reference, extract the schema name from the ref attribute
                                if hasattr(media_type_schema, "ref"):
                                    ref = media_type_schema.ref
                                    if "/" in ref:
                                        actual_schema_name = ref.split("/")[-1]

                            # If not extracted yet, try from model_dump
                            if not actual_schema_name:
                                temp_dict = (
                                    media_type_schema.model_dump()
                                    if hasattr(media_type_schema, "model_dump")
                                    else media_type_schema
                                )
                                if isinstance(temp_dict, dict):
                                    actual_schema_name = (
                                        self._extract_schema_name_from_ref(temp_dict)
                                    )

                            # Clean the schema name
                            clean_schema_name = None
                            if actual_schema_name:
                                clean_schema_name = self._clean_schema_name(
                                    actual_schema_name
                                )

                            title = (
                                clean_schema_name or base_response_name
                                if status_code.startswith("2")
                                else clean_schema_name
                                or f"{base_response_name}{status_code}"
                            )

                            # If we found a schema name from $ref, update base_response_name for success responses
                            if status_code.startswith("2") and clean_schema_name:
                                base_response_name = clean_schema_name

                            # If this references a component schema, don't generate it
                            if (
                                clean_schema_name
                                and clean_schema_name in self.component_schemas
                            ):
                                referenced_components.add(clean_schema_name)
                            else:
                                # Resolve reference if needed
                                schema = resolve_reference(
                                    media_type_schema, self.raw_spec
                                )
                                if isinstance(schema, dict):
                                    schema_dict = schema
                                elif hasattr(media_type_schema, "model_dump"):
                                    schema_dict = media_type_schema.model_dump()
                                else:
                                    schema_dict = (
                                        media_type_schema
                                        if isinstance(media_type_schema, dict)
                                        else {}
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
                            schema_dict = content_data["schema"]

                            # Extract schema name from $ref if present
                            actual_schema_name = self._extract_schema_name_from_ref(
                                schema_dict
                            )

                            # Clean the schema name
                            clean_schema_name = None
                            if actual_schema_name:
                                clean_schema_name = self._clean_schema_name(
                                    actual_schema_name
                                )

                            title = (
                                clean_schema_name or base_response_name
                                if status_code.startswith("2")
                                else clean_schema_name
                                or f"{base_response_name}{status_code}"
                            )

                            # If we found a schema name from $ref, update base_response_name for success responses
                            if status_code.startswith("2") and clean_schema_name:
                                base_response_name = clean_schema_name

                            # If this references a component schema, don't generate it
                            if (
                                clean_schema_name
                                and clean_schema_name in self.component_schemas
                            ):
                                referenced_components.add(clean_schema_name)
                            else:
                                model = generate_model_from_schema(
                                    schema_dict, title, self.raw_spec
                                )
                                if model:
                                    generated_models.append(model)

        # Always ensure we have a response model for success responses
        if success_responses:
            # Check if base_response_name is a component (already generated)
            if base_response_name in self.component_schemas:
                referenced_components.add(base_response_name)
            else:
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
            referenced_components,
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

        # Determine request model name
        request_model = f"{method_prefix}Request"

        # Check if we need combined params (path params + request body)
        has_combined_params = bool(path.count("{"))  # Has path parameters

        return {
            "method": method,
            "method_prefix": method_prefix,
            "name": operation_name,
            "request_model": request_model,
            "success_code": response_info["success_code"],
            "has_query_params": has_query_params,
            "response_model": response_info["response_model"],
            "has_combined_params": has_combined_params,
        }

    def _write_operation_file(
        self,
        operation_file: Path,
        path: str,
        path_params: List[Dict[str, Any]],
        all_models: List[str],
        referenced_components: set[str],
        operations_info: List[Dict[str, Any]],
    ) -> None:
        """Write the combined operation.py file with models and API operations."""
        operation_file.parent.mkdir(parents=True, exist_ok=True)

        # Deduplicate models
        deduplicated_models = deduplicate_models(all_models)

        # Prepare template context
        template_path = path.replace("{", "$").replace("}", "")
        python_path = convert_path_to_snake_case(path)
        param_examples = (
            ", ".join([f'{p["name"]}="value"' for p in path_params])
            if path_params
            else ""
        )

        # Calculate import depth for components
        relative_path = operation_file.relative_to(self.output_root)
        import_depth = len(relative_path.parts) - 1

        # Render combined template
        rendered = self.renderer.render_operation(
            path=path,
            template_path=template_path,
            python_path=python_path,
            has_path_params=bool(path_params),
            param_examples=param_examples,
            models=deduplicated_models,
            operations=operations_info,
            referenced_components=list(referenced_components),
            import_depth=import_depth,
        )

        with open(operation_file, "w") as f:
            f.write(rendered)

        print(f"✅ Operation: {truncate_path(operation_file)}")

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
