from typing import Any

from unique_toolkit._common.utils.jinja.sandbox import sandboxed_template
from unique_toolkit._common.utils.jinja.schema import Jinja2PromptParams


def render_template(
    template: str, params: Jinja2PromptParams | dict[str, Any] | None = None, **kwargs
) -> str:
    params = params or {}

    if isinstance(params, Jinja2PromptParams):
        params = params.model_dump(exclude_none=True, mode="json")

    params.update(kwargs)

    return sandboxed_template(template, lstrip_blocks=True).render(**params)
