from functools import cache

from jinja2 import Template, TemplateError
from jinja2.sandbox import SandboxedEnvironment

__all__ = ["TemplateError", "sandboxed_template"]


@cache
def _sandboxed_environment(*, lstrip_blocks: bool) -> SandboxedEnvironment:
    return SandboxedEnvironment(lstrip_blocks=lstrip_blocks)


def sandboxed_template(source: str, *, lstrip_blocks: bool = False) -> Template:
    """Compile a Jinja template under Jinja's sandbox restrictions.

    Use this for templates that come from configuration. An expression the
    sandbox rejects raises ``jinja2.exceptions.SecurityError``.
    """
    return _sandboxed_environment(lstrip_blocks=lstrip_blocks).from_string(source)
