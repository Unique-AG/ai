from pathlib import Path


def _load_template(filename: str) -> str:
    """Load a Jinja2 template file from the context_relevancy directory."""
    template_path = Path(__file__).parent / filename
    with open(template_path, "r") as f:
        return f.read()


def system_prompt_loader():
    return _load_template("system_prompt.j2")


def user_prompt_loader():
    return _load_template("user_prompt.j2")
