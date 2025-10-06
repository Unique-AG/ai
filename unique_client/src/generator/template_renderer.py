"""Template rendering for generated code."""

from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader


class TemplateRenderer:
    """Handles Jinja2 template rendering for code generation."""

    def __init__(self, template_dir: Path):
        """Initialize the template renderer.

        Args:
            template_dir: Directory containing Jinja2 templates (should be generator/templates/)
        """
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_endpoint_init(
        self,
        operations: List[str],
        subdirs: List[str],
        exports: List[str],
    ) -> str:
        """Render endpoint __init__.py file.

        Args:
            operations: List of operation names to import
            subdirs: List of subdirectory names to import
            exports: Combined list of exports

        Returns:
            Rendered __init__.py content
        """
        template = self.env.get_template("endpoint_init_template.jinja2")
        return template.render(
            operations=operations,
            subdirs=subdirs,
            exports=exports,
        )

    def render_parent_init(self, subdirs: List[str]) -> str:
        """Render parent directory __init__.py file.

        Args:
            subdirs: List of subdirectory names to import and export

        Returns:
            Rendered __init__.py content
        """
        template = self.env.get_template("parent_init_template.jinja2")
        return template.render(subdirs=subdirs)

    def render_components(self, models: List[str]) -> str:
        """Render the components.py file with all OpenAPI component schemas.

        Args:
            models: List of generated Pydantic model class definitions

        Returns:
            Rendered components.py content
        """
        template = self.env.get_template("components.py.jinja2")
        return template.render(models=models)

    def render_operation(
        self,
        path: str,
        template_path: str,
        python_path: str,
        has_path_params: bool,
        param_examples: str,
        models: List[str],
        operations: List[Dict[str, Any]],
        referenced_components: List[str] | None = None,
        import_depth: int = 2,
    ) -> str:
        """Render the combined operation.py file with models and API operations.

        Args:
            path: OpenAPI path
            template_path: Path with $ instead of {}
            python_path: Path with snake_case parameters
            has_path_params: Whether path has parameters
            param_examples: Example parameter string
            models: List of model class definitions
            operations: List of operation metadata
            referenced_components: List of component schema names to import
            import_depth: Number of parent directories to traverse for components import

        Returns:
            Rendered operation.py content
        """
        if not referenced_components:
            referenced_components = []

        template = self.env.get_template("operation_template.jinja2")
        return template.render(
            path=path,
            template_path=template_path,
            python_path=python_path,
            has_path_params=has_path_params,
            param_examples=param_examples,
            models=models,
            operations=operations,
            referenced_components=sorted(referenced_components),
            import_depth=import_depth,
        )
