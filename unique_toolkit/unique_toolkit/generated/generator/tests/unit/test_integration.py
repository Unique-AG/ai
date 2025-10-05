"""Integration tests for end-to-end route generation."""

import pytest
from openapi_pydantic import OpenAPI

from ...init_generator import InitGenerator
from ...path_processor import PathProcessor


class TestEndToEndGeneration:
    """Integration tests for complete route generation."""

    @pytest.mark.ai_generated
    def test_full_generation_pipeline__creates_working_sdk__for_simple_endpoint(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify complete pipeline generates working SDK structure.
        Why: All components must work together for functional SDK.
        Setup: Sample spec with GET and POST operations.
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        output_root = tmp_path / "generated_routes"
        processor = PathProcessor(template_dir, output_root, sample_openapi_spec)
        init_gen = InitGenerator(template_dir)

        # Act
        # Step 1: Process path
        processor.process_path("/test/endpoint", openapi.paths["/test/endpoint"])

        # Step 2: Update endpoint inits
        init_gen.update_endpoint_init_files(output_root)

        # Step 3: Generate parent inits
        init_gen.generate_parent_init_files(output_root)

        # Assert - Check complete structure
        endpoint_dir = output_root / "test" / "endpoint"
        assert endpoint_dir.exists()
        assert (endpoint_dir / "models.py").exists()
        assert (endpoint_dir / "path_operation.py").exists()
        assert (endpoint_dir / "__init__.py").exists()

        # Verify __init__ exports operations
        init_content = (endpoint_dir / "__init__.py").read_text()
        assert "FindAll" in init_content
        assert "Create" in init_content

        # Verify parent __init__ exists
        test_dir_init = output_root / "test" / "__init__.py"
        assert test_dir_init.exists()
        parent_content = test_dir_init.read_text()
        assert "from . import endpoint" in parent_content

    @pytest.mark.ai_generated
    def test_full_generation_pipeline__handles_nested_routes__correctly(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify nested routes create proper directory hierarchy.
        Why: Routes like /folder/{scopeId}/access need nested structure.
        Setup: Spec with parameterized nested path.
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        output_root = tmp_path / "generated_routes"
        processor = PathProcessor(template_dir, output_root, sample_openapi_spec)
        init_gen = InitGenerator(template_dir)

        # Act
        processor.process_path(
            "/test/endpoint/{itemId}", openapi.paths["/test/endpoint/{itemId}"]
        )
        init_gen.update_endpoint_init_files(output_root)
        init_gen.generate_parent_init_files(output_root)

        # Assert
        nested_dir = output_root / "test" / "endpoint" / "itemId"
        assert nested_dir.exists()
        assert (nested_dir / "models.py").exists()
        assert (nested_dir / "path_operation.py").exists()

        # Verify PathParams in models
        models_content = (nested_dir / "models.py").read_text()
        assert "PathParams" in models_content

    @pytest.mark.ai_generated
    def test_selective_path_generation__only_processes_specified_paths__correctly(
        self, tmp_path, template_dir, sample_openapi_spec
    ):
        """
        Purpose: Verify selective generation only affects specified paths.
        Why: Users need to regenerate individual endpoints without full rebuild.
        Setup: Spec with multiple paths, generate only one.
        """
        # Arrange
        openapi = OpenAPI.model_validate(sample_openapi_spec)
        output_root = tmp_path / "generated_routes"
        processor = PathProcessor(template_dir, output_root, sample_openapi_spec)

        # Act - Generate only /test/endpoint, not the parameterized one
        processor.process_path("/test/endpoint", openapi.paths["/test/endpoint"])

        # Assert
        endpoint_dir = output_root / "test" / "endpoint"
        assert endpoint_dir.exists()

        # The parameterized path should not be generated
        nested_dir = output_root / "test" / "endpoint" / "itemId"
        assert not nested_dir.exists()


class TestErrorHandling:
    """Tests for error handling in generation pipeline."""

    @pytest.mark.ai_generated
    def test_generation__continues_on_schema_error__with_fallback_model(
        self, tmp_path, template_dir
    ):
        """
        Purpose: Verify generation continues when individual schema fails.
        Why: One bad schema shouldn't break entire SDK generation.
        Setup: Spec with malformed schema that triggers error.
        """
        # Arrange
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "post": {
                        "operationId": "create",
                        "responses": {
                            "201": {
                                "description": "Created",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            # Deliberately incomplete schema
                                            "type": "object"
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
            "components": {"schemas": {}},
        }

        openapi = OpenAPI.model_validate(spec)
        processor = PathProcessor(template_dir, tmp_path, spec)

        # Act
        processor.process_path("/test", openapi.paths["/test"])

        # Assert - Files should still be created with fallback models
        endpoint_dir = tmp_path / "test"
        assert endpoint_dir.exists()
        assert (endpoint_dir / "models.py").exists()

        # Should have at least a fallback response model
        models_content = (endpoint_dir / "models.py").read_text()
        assert "CreateResponse" in models_content or "PostRequest" in models_content
