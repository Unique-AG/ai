from pathlib import Path


def get_parent_dir(file_path: str) -> Path:
    return Path(file_path).parent


def load_template(parent_dir: Path, template_name: str) -> str:
    with open(parent_dir / template_name, "r") as file:
        return file.read().strip()
