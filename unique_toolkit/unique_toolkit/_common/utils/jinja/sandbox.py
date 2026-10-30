from functools import cache

from jinja2 import Template
from jinja2.sandbox import SandboxedEnvironment


@cache
def _sandboxed_environment(*, lstrip_blocks: bool) -> SandboxedEnvironment:
    return SandboxedEnvironment(lstrip_blocks=lstrip_blocks)


def sandboxed_template(source: str, *, lstrip_blocks: bool = False) -> Template:
    """Compile a Jinja template that cannot reach Python internals.

    Prompt templates come from space module configuration, which users can edit,
    so a plain ``jinja2.Template`` would let ``{{ x.__init__.__globals__ ... }}``
    execute code. Rendering an unsafe expression raises ``jinja2.exceptions.SecurityError``.
    """
    return _sandboxed_environment(lstrip_blocks=lstrip_blocks).from_string(source)
