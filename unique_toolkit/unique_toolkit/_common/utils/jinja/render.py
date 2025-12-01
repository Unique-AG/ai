from typing import Any

from jinja2 import Template

from unique_toolkit._common.utils.jinja.schema import Jinja2PromptParams


def render_template(
    template: str, params: Jinja2PromptParams | dict[str, Any] | None = None, **kwargs
) -> str:
    params = params or {}

    if isinstance(params, Jinja2PromptParams):
        params = params.model_dump(exclude_none=True, mode="json")

    params.update(kwargs)

    return Template(template, lstrip_blocks=True).render(**params)
