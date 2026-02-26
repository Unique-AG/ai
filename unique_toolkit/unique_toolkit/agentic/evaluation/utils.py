from pathlib import Path


def load_template(parent_dir: Path, filename: str) -> str:
    """Load a Jinja2 template file from the hallucination directory."""
    template_path = parent_dir / filename
    with open(template_path, "r") as f:
        return f.read()
