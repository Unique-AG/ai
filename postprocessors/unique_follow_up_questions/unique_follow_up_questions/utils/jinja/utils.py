from jinja2 import Environment
from jinja2.nodes import Const, Getattr, Getitem, Name
from pydantic import BaseModel


class TemplateValidationResult(BaseModel):
    is_valid: bool
    missing_placeholders: list[str]
    optional_placeholders: list[str]
    unexpected_placeholders: list[str]


def _get_nested_variables(node):
    """Recursively extract all variable references from a Jinja2 AST node."""
    variables = set()

    if isinstance(node, Name):
        variables.add(node.name)
    elif isinstance(node, (Getattr, Getitem)):
        # For nested attributes like example.category
        if isinstance(node.node, Name):
            if isinstance(node, Getattr):
                variables.add(f"{node.node.name}.{node.attr}")
            else:  # Getitem
                if isinstance(node.arg, Const):
                    variables.add(f"{node.node.name}.{node.arg.value}")
                else:
                    # For dynamic indices, just use the base variable
                    variables.add(node.node.name)
        # Recursively process nested nodes
        variables.update(_get_nested_variables(node.node))

    # Process child nodes
    for child in node.iter_child_nodes():
        variables.update(_get_nested_variables(child))

    return variables


def validate_template_placeholders(
    template_content: str,
    required_placeholders: set[str],
    optional_placeholders: set[str],
) -> TemplateValidationResult:
    """
    Validates that all required placeholders in the template are present.
    Handles both top-level and nested variables (e.g. example.category).

    Args:
        template_content (str): The content of the Jinja template
        required_placeholders (set[str]): Set of required placeholder names
        optional_placeholders (set[str]): Set of optional placeholder names

    Returns:
        TemplateValidationResult: A result object containing validation information
    """
    # Create a Jinja environment
    env = Environment()

    # Parse the template and get all variables including nested ones
    ast = env.parse(template_content)
    template_vars = _get_nested_variables(ast)

    # Check for missing required placeholders
    missing_placeholders = required_placeholders - template_vars

    # Check for optional placeholders present
    present_optional = optional_placeholders & template_vars

    # Check for any unexpected placeholders
    unexpected_placeholders = template_vars - (
        required_placeholders | optional_placeholders
    )

    return TemplateValidationResult(
        is_valid=len(missing_placeholders) == 0,
        missing_placeholders=sorted(list(missing_placeholders)),
        optional_placeholders=sorted(list(present_optional)),
        unexpected_placeholders=sorted(list(unexpected_placeholders)),
    )
