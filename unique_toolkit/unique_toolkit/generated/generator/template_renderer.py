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

    def render_models(
        self,
        path: str,
        template_path: str,
        has_path_params: bool,
        param_examples: str,
        models: List[str],
    ) -> str:
        """Render the models.py file.

        Args:
            path: OpenAPI path
            template_path: Path with $ instead of {}
            has_path_params: Whether path has parameters
            param_examples: Example parameter string
            models: List of model class definitions

        Returns:
            Rendered models file content
        """
        template = self.env.get_template("model_template.jinja2")
        return template.render(
            path=path,
            template_path=template_path,
            has_path_params=has_path_params,
            param_examples=param_examples,
            models=models,
        )

    def render_api_client(
        self,
        path: str,
        python_path: str,
        has_path_params: bool,
        operations: List[Dict[str, Any]],
        class_name: str,
    ) -> str:
        """Render the path_operation.py file.

        Args:
            path: Original OpenAPI path
            python_path: Path with snake_case parameters
            has_path_params: Whether path has parameters
            operations: List of operation metadata
            class_name: PascalCase class name for the endpoint

        Returns:
            Rendered API client file content
        """
        template = self.env.get_template("api_template.jinja2")
        return template.render(
            path=python_path,
            has_path_params=has_path_params,
            operations=operations,
            class_name=class_name,
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
