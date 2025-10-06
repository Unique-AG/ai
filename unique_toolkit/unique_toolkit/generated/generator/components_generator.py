"""Generate centralized components.py from OpenAPI schemas."""

from pathlib import Path
from typing import Any, Dict

from .schema_generator import generate_model_from_schema
from .template_renderer import TemplateRenderer
from .utils import deduplicate_models


def generate_components_file(
    raw_spec: Dict[str, Any], output_root: Path, template_dir: Path
) -> None:
    """Generate a single components.py with all schemas from OpenAPI spec.

    Args:
        raw_spec: Raw OpenAPI specification dictionary
        output_root: Root directory for generated routes
        template_dir: Directory containing Jinja2 templates
    """
    schemas = raw_spec.get("components", {}).get("schemas", {})

    if not schemas:
        print("  No component schemas found in OpenAPI spec")
        return

    print(f"  Generating {len(schemas)} component schemas...")

    all_models = []
    for schema_name, schema_def in sorted(schemas.items()):
        # Clean up schema name: remove "Public" prefix and "Dto" suffix
        clean_name = schema_name
        if clean_name.startswith("Public"):
            clean_name = clean_name[6:]  # Remove "Public"
        if clean_name.endswith("Dto"):
            clean_name = clean_name[:-3]  # Remove "Dto"

        # Generate each component schema with cleaned name
        model = generate_model_from_schema(schema_def, clean_name, raw_spec)
        if model:
            all_models.append(model)

    # Deduplicate models (nested schemas may be generated multiple times)
    deduplicated_models = deduplicate_models(all_models)
    print(f"  After deduplication: {len(deduplicated_models)} unique models")

    # Render using template
    renderer = TemplateRenderer(template_dir)
    rendered = renderer.render_components(models=deduplicated_models)

    # Write to generated_routes/components.py
    components_file = output_root / "components.py"
    components_file.parent.mkdir(parents=True, exist_ok=True)

    with open(components_file, "w") as f:
        f.write(rendered)

    print(f"✅ Components: {components_file.relative_to(output_root.parent)}")
