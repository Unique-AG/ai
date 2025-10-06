"""Tests for __init__.py file generation."""

import pytest
from generator.init_generator import InitGenerator


class TestInitGenerator:
    """Tests for InitGenerator class."""

    @pytest.mark.ai_generated
    def test_update_endpoint_init_files__adds_subdirs__to_existing_init(
        self, tmp_path, template_dir
    ):
        """
        Purpose: Verify endpoint __init__ files are updated with subdirectories.
        Why: Enables nested imports like client.folder.scopeId.access.
        Setup: Endpoint dir with path_operation.py, __init__.py, and subdir.
        """
        # Arrange
        endpoint_dir = tmp_path / "public" / "folder"
        endpoint_dir.mkdir(parents=True)

        # Create operation.py with an operation
        (endpoint_dir / "operation.py").write_text(
            "CreateFolder = build_requestor(...)"
        )

        # Create initial __init__.py
        (endpoint_dir / "__init__.py").write_text(
            "from .operation import CreateFolder\n__all__ = ['CreateFolder']\n"
        )

        # Create subdirectory with __init__.py
        subdir = endpoint_dir / "scopeId"
        subdir.mkdir()
        (subdir / "__init__.py").write_text("")
        (subdir / "operation.py").write_text("DeleteFolder = build_requestor(...)")

        generator = InitGenerator(template_dir)

        # Act
        generator.update_endpoint_init_files(tmp_path)

        # Assert
        init_content = (endpoint_dir / "__init__.py").read_text()
        assert "'CreateFolder'" in init_content
        assert "'scopeId'" in init_content
        # Template may format differently, check both are in exports
        assert "CreateFolder" in init_content and "scopeId" in init_content

    @pytest.mark.ai_generated
    def test_generate_parent_init_files__creates_init__for_parent_dirs(
        self, tmp_path, template_dir
    ):
        """
        Purpose: Verify parent directories get __init__ files with submodule imports.
        Why: Enables imports like 'import generated_routes.public as client'.
        Setup: Directory tree with endpoints but no parent __init__.
        """
        # Arrange
        public_dir = tmp_path / "public"
        folder_dir = public_dir / "folder"
        folder_dir.mkdir(parents=True)

        # Create endpoint __init__.py
        (folder_dir / "__init__.py").write_text("")
        (folder_dir / "operation.py").write_text("")

        messages_dir = public_dir / "messages"
        messages_dir.mkdir()
        (messages_dir / "__init__.py").write_text("")
        (messages_dir / "operation.py").write_text("")

        generator = InitGenerator(template_dir)

        # Act
        generator.generate_parent_init_files(tmp_path)

        # Assert
        parent_init = public_dir / "__init__.py"
        assert parent_init.exists()
        content = parent_init.read_text()
        assert "from . import folder" in content
        assert "from . import messages" in content
