from pathlib import Path


def load_template(parent_dir: Path, template_name: str) -> str:
    with open(parent_dir / template_name, "r") as file:
        return file.read().strip()
