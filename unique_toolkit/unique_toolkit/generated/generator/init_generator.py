"""Generate __init__.py files for the route package structure."""

import os
import re
from pathlib import Path

from .template_renderer import TemplateRenderer
from .utils import truncate_path


class InitGenerator:
    """Handles generation of __init__.py files."""

    def __init__(self, template_dir: Path):
        """Initialize the init generator.

        Args:
            template_dir: Directory containing Jinja2 templates
        """
        self.renderer = TemplateRenderer(template_dir)

    def update_endpoint_init_files(self, output_root: Path) -> None:
        """Update endpoint-level __init__.py files to include subdirectories.

        This is a post-processing step that runs after all endpoints are generated,
        ensuring that each endpoint's __init__.py exposes both operations
        and any subdirectories (for nested routes).

        Args:
            output_root: Root directory of generated routes
        """
        print("\n🔧 Updating endpoint __init__.py files with subdirectories...")

        # Find all directories with path_operation.py (these are endpoints)
        for root, dirs, files in os.walk(output_root):
            if "path_operation.py" not in files:
                continue

            root_path = Path(root)
            init_file = root_path / "__init__.py"
            path_operation_file = root_path / "path_operation.py"

            if not init_file.exists() or not path_operation_file.exists():
                continue

            # Read path_operation.py to extract operation names
            with open(path_operation_file, "r") as f:
                path_op_content = f.read()

            # Extract operation names (variables assigned with build_requestor)
            # Pattern: operation_name = build_requestor(...)
            operation_names = re.findall(
                r"^(\w+)\s*=\s*build_requestor\(", path_op_content, re.MULTILINE
            )

            if not operation_names:
                continue

            # Find subdirectories with __init__.py
            subdirs = []
            for item in root_path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    subdirs.append(item.name)

            subdirs.sort()

            # Regenerate the __init__.py with operations and subdirectories using template
            exports = operation_names + subdirs
            init_rendered = self.renderer.render_endpoint_init(
                operations=operation_names,
                subdirs=subdirs,
                exports=exports,
            )

            with open(init_file, "w") as f:
                f.write(init_rendered)

            if subdirs or operation_names:
                print(f"✅ Init: {truncate_path(init_file)}")

    def generate_parent_init_files(self, output_root: Path) -> None:
        """Generate __init__.py files for all parent directories in the route tree.

        This creates __init__.py files that expose submodules, making imports like
        'import unique_toolkit.generated.generated_routes.public as client' work.

        Args:
            output_root: Root directory of generated routes
        """
        print("\n🔧 Generating parent __init__.py files...")

        # Collect all directories that need __init__.py files
        dirs_to_process = set()

        # Walk through all directories in the output_root
        for root, dirs, files in os.walk(output_root):
            root_path = Path(root)

            # Skip if this is a leaf directory (has path_operation.py)
            if "path_operation.py" in files:
                continue

            # Check if this directory has subdirectories with __init__.py
            has_python_subdirs = False
            for subdir in dirs:
                subdir_path = root_path / subdir
                if (subdir_path / "__init__.py").exists():
                    has_python_subdirs = True
                    break

            if has_python_subdirs:
                dirs_to_process.add(root_path)

        # Generate __init__.py for each directory
        for dir_path in sorted(dirs_to_process):
            # Get immediate subdirectories that have __init__.py
            subdirs = []
            for item in dir_path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    subdirs.append(item.name)

            if subdirs:
                init_file = dir_path / "__init__.py"

                # Sort subdirs for consistent output
                subdirs.sort()

                # Render template
                init_rendered = self.renderer.render_parent_init(subdirs=subdirs)

                with open(init_file, "w") as f:
                    f.write(init_rendered)

                print(f"✅ Parent: {truncate_path(init_file)}")
