from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

from unique_swot.services.collection.schema import SourceChunk

# Get the directory containing this file
_PROMPTS_DIR = Path(__file__).parent

# Create Jinja2 environment with the prompts directory as the base
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


CHUNK_TEMPLATE: Template = _jinja_env.get_template("chunk_template.j2")


def batch_parser(batch: list[SourceChunk]) -> str:
    return CHUNK_TEMPLATE.render(chunk_list=batch)
