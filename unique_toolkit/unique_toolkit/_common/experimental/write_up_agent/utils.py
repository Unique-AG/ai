from pathlib import Path


def template_loader(parent_dir: Path, template_name: str) -> str:
    """
    Load a Jinja2 template file from the filesystem.

    Args:
        parent_dir: Path object pointing to the directory containing the template
        template_name: Name of the template file to load (e.g., 'template.j2')

    Returns:
        Template content as a string

    Raises:
        FileNotFoundError: If the template file does not exist
        IOError: If there's an error reading the template file

    Example:
        >>> from pathlib import Path
        >>> template = template_loader(Path(__file__).parent, "my_template.j2")
    """
    template_path = parent_dir / template_name
    return template_path.read_text()
