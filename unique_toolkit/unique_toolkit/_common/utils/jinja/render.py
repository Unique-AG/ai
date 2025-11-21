from typing import Any

from _common.utils.jinja.schema import Jinja2PromptParams
from jinja2 import Template


def render_template(template: str, params: Jinja2PromptParams | dict[str, Any]) -> str:
    if isinstance(params, Jinja2PromptParams):
        params = params.model_dump(exclude_none=True, mode="json")

    return Template(template, lstrip_blocks=True).render(**params)
