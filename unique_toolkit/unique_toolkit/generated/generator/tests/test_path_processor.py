"""Tests for OpenAPI path processing."""

import pytest
from openapi_pydantic import OpenAPI

from ..path_processor import PathProcessor


class TestPathProcessor:
    """Tests for PathProcessor class."""

    @pytest.mark.ai_generated
    def test_process_path__generates_all_files__for_endpoint(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify all necessary files are created for an endpoint.
        Why: Complete SDK generation requires models, operations, and __init__.
        Setup: Sample spec with /test/endpoint, temp output directory.
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        path = "/test/endpoint"
        path_item = openapi.paths[path]

        output_root = tmp_path / "generated_routes"
        processor = PathProcessor(template_dir, output_root, sample_openapi_spec)

        # Act
        processor.process_path(path, path_item)

        # Assert
        endpoint_dir = output_root / "test" / "endpoint"
        assert (endpoint_dir / "models.py").exists()
        assert (endpoint_dir / "path_operation.py").exists()
        assert (endpoint_dir / "__init__.py").exists()

    @pytest.mark.ai_generated
    def test_process_path__capitalizes_operation_names__for_sdk(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify operation names are capitalized (findAll -> FindAll).
        Why: Consistent naming convention for SDK operations.
        Setup: Spec with operationId="findAll".
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        path = "/test/endpoint"
        path_item = openapi.paths[path]

        output_root = tmp_path / "generated_routes"
        processor = PathProcessor(template_dir, output_root, sample_openapi_spec)

        # Act
        processor.process_path(path, path_item)

        # Assert
        path_operation_content = (
            output_root / "test" / "endpoint" / "path_operation.py"
        ).read_text()
        assert "FindAll" in path_operation_content
        assert "Create" in path_operation_content

    @pytest.mark.ai_generated
    def test_process_path__resolves_schema_refs__in_responses(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify $ref in response schemas are resolved to actual models.
        Why: Response models need full schema to generate proper Pydantic classes.
        Setup: POST operation with $ref to TestResponse component.
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        path = "/test/endpoint"
        path_item = openapi.paths[path]

        output_root = tmp_path / "generated_routes"
        processor = PathProcessor(template_dir, output_root, sample_openapi_spec)

        # Act
        processor.process_path(path, path_item)

        # Assert
        models_content = (output_root / "test" / "endpoint" / "models.py").read_text()
        assert "class CreateResponse(BaseModel):" in models_content
        # Should have properties from TestResponse schema
        assert "id" in models_content or "name" in models_content

    @pytest.mark.ai_generated
    def test_process_path__generates_path_params__for_parameterized_routes(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify PathParams model is generated for routes with path parameters.
        Why: Routes like /folder/{scopeId} need path parameter validation.
        Setup: Path with {itemId} parameter.
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        path = "/test/endpoint/{itemId}"
        path_item = openapi.paths[path]

        output_root = tmp_path / "generated_routes"
        processor = PathProcessor(template_dir, output_root, sample_openapi_spec)

        # Act
        processor.process_path(path, path_item)

        # Assert
        models_content = (
            output_root / "test" / "endpoint" / "itemId" / "models.py"
        ).read_text()
        assert "class PathParams(BaseModel):" in models_content
        assert "item_id" in models_content  # snake_case conversion


class TestPathProcessorHelpers:
    """Tests for PathProcessor helper methods."""

    @pytest.mark.ai_generated
    def test_extract_path_params__finds_params__from_path_item(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify path parameters are correctly extracted.
        Why: Path param extraction is critical for proper URL construction.
        Setup: PathItem with itemId parameter.
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        path_item = openapi.paths["/test/endpoint/{itemId}"]
        methods = {"delete": path_item.delete}

        processor = PathProcessor(template_dir, tmp_path, sample_openapi_spec)

        # Act
        result = processor._extract_path_params(path_item, methods)

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "itemId"
        assert result[0]["param_in"] == "path"  # openapi_pydantic uses param_in not in

    @pytest.mark.ai_generated
    def test_collect_operation_info__uses_descriptive_response_name__from_operation_id(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify response model names are based on operationId.
        Why: CreateResponse is more descriptive than PostResponse201.
        Setup: Operation with operationId="create".
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        operation = openapi.paths["/test/endpoint"].post
        processor = PathProcessor(template_dir, tmp_path, sample_openapi_spec)

        response_info = {
            "success_code": "201",
            "response_model": "CreateResponse",
            "has_success_responses": True,
        }

        # Act
        result = processor._collect_operation_info(
            operation,
            "post",
            "Post",
            "/test/endpoint",
            response_info,
            [],
        )

        # Assert
        assert result is not None
        assert result["name"] == "Create"  # Capitalized operationId
        assert result["response_model"] == "CreateResponse"
