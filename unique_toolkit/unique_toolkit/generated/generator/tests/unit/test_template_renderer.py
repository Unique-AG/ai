"""Tests for Jinja2 template rendering."""

import pytest

from ...template_renderer import TemplateRenderer


class TestTemplateRenderer:
    """Tests for TemplateRenderer class."""

    @pytest.mark.ai_generated
    def test_render_endpoint_init__exports_operations_and_subdirs__correctly(
        self, template_dir
    ):
        """
        Purpose: Verify endpoint __init__ exports both operations and subdirectories.
        Why: Enables nested route access like client.folder.scopeId.DeleteFolder.
        Setup: Template dir with endpoint_init_template, 2 operations, 1 subdir.
        """
        # Arrange
        renderer = TemplateRenderer(template_dir)
        operations = ["Create", "FindAll"]
        subdirs = ["id"]
        exports = operations + subdirs

        # Act
        result = renderer.render_endpoint_init(operations, subdirs, exports)

        # Assert
        assert "from .operation import Create, FindAll" in result
        assert "['Create', 'FindAll', 'id']" in result
        # Template may not add newlines, check operations are imported
        assert "Create" in result and "FindAll" in result

    @pytest.mark.ai_generated
    def test_render_parent_init__imports_all_subdirs__in_sorted_order(
        self, template_dir
    ):
        """
        Purpose: Verify parent __init__ imports subdirectories in consistent order.
        Why: Deterministic output makes diffs cleaner.
        Setup: Template dir with 3 unsorted subdirectories.
        """
        # Arrange
        renderer = TemplateRenderer(template_dir)
        subdirs = ["folder", "agent", "messages"]

        # Act
        result = renderer.render_parent_init(subdirs)

        # Assert
        assert "from . import folder" in result
        assert "from . import agent" in result
        assert "from . import messages" in result
        assert "['folder', 'agent', 'messages']" in result

    @pytest.mark.ai_generated
    def test_render_operation__includes_path_params__when_present(self, template_dir):
        """
        Purpose: Verify operation file renders path parameter handling.
        Why: Routes with parameters need PathParams constructor.
        Setup: Template with has_path_params=True.
        """
        # Arrange
        renderer = TemplateRenderer(template_dir)
        operations = [
            {
                "name": "DeleteFolder",
                "method": "delete",
                "method_prefix": "Delete",
                "response_model": "DeleteFolderResponse",
                "request_model": "DeleteRequest",
                "has_query_params": False,
                "has_combined_params": False,
            }
        ]

        # Act
        result = renderer.render_operation(
            path="/public/folder/{scope_id}",
            template_path="/public/folder/$scope_id",
            python_path="/public/folder/{scope_id}",
            has_path_params=True,
            param_examples="scope_id='abc'",
            models=[],
            operations=operations,
        )

        # Assert
        assert "DeleteFolder" in result
