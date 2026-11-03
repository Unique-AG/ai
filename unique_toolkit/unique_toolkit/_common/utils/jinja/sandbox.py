from functools import cache

from jinja2 import Template, TemplateError, nodes
from jinja2.exceptions import SecurityError
from jinja2.sandbox import (
    UNSAFE_ASYNC_GENERATOR_ATTRIBUTES,
    UNSAFE_COROUTINE_ATTRIBUTES,
    UNSAFE_FUNCTION_ATTRIBUTES,
    UNSAFE_GENERATOR_ATTRIBUTES,
    UNSAFE_METHOD_ATTRIBUTES,
    SandboxedEnvironment,
)

__all__ = ["TemplateError", "sandboxed_template", "validate_sandboxed_template"]

_UNSAFE_STATIC_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "mro",
        *UNSAFE_FUNCTION_ATTRIBUTES,
        *UNSAFE_METHOD_ATTRIBUTES,
        *UNSAFE_GENERATOR_ATTRIBUTES,
        *UNSAFE_COROUTINE_ATTRIBUTES,
        *UNSAFE_ASYNC_GENERATOR_ATTRIBUTES,
    }
)


@cache
def _sandboxed_environment(*, lstrip_blocks: bool) -> SandboxedEnvironment:
    return SandboxedEnvironment(lstrip_blocks=lstrip_blocks)


def sandboxed_template(source: str, *, lstrip_blocks: bool = False) -> Template:
    """Compile a Jinja template under Jinja's sandbox restrictions.

    Use this for templates that come from configuration. An expression the
    sandbox rejects raises ``jinja2.exceptions.SecurityError``.
    """
    return _sandboxed_environment(lstrip_blocks=lstrip_blocks).from_string(source)


def validate_sandboxed_template(source: str, *, lstrip_blocks: bool = False) -> str:
    """Validate that ``source`` compiles and accesses no sandbox-forbidden attributes.

    Raises ``jinja2.TemplateSyntaxError`` on malformed syntax (and top-level
    unknown filters/tests; filters inside conditionals are resolved by Jinja at
    render time) and ``jinja2.exceptions.SecurityError`` on static dot-access to
    private or internal Python attributes.
    """
    env = _sandboxed_environment(lstrip_blocks=lstrip_blocks)
    ast = env.parse(source)
    for node in ast.find_all(nodes.Getattr):
        if node.attr.startswith("_") or node.attr in _UNSAFE_STATIC_ATTRIBUTES:
            raise SecurityError("access to private or internal attribute is unsafe.")
    env.from_string(source)
    return source
