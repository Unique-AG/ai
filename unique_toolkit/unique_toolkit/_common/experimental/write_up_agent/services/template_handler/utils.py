"""Template utilities."""

from jinja2 import Environment
from jinja2.nodes import For, Getattr, Name
from pydantic import BaseModel


class TemplateStructureInfo(BaseModel):
    """Information about the structure expected by a Jinja template.

    Attributes:
        grouping_columns: List of column names detected from {{ group.column }} patterns
        row_columns: List of column names detected from {{ row.column }} patterns
        expects_groups: True if template iterates over 'groups' variable
        expects_rows: True if template iterates over 'rows' variable
    """

    grouping_columns: list[str]
    row_columns: list[str]
    expects_groups: bool
    expects_rows: bool


# TODO [UN-16142]: Simplify template logic
def parse_template(template_str: str) -> TemplateStructureInfo:
    """
    Parse a Jinja template to extract structure information.

    The parser detects:
    - {% for X in groups %} → expects_groups = True, X becomes the group variable
    - {{ X.column_name }} → grouping_columns contains 'column_name' (excluding 'rows', 'instructions')
    - {% for Y in rows %} or {% for Y in X.rows %} → expects_rows = True
    - {{ row.column_name }} → row_columns contains 'column_name'

    Args:
        template_str: Jinja template string to parse

    Returns:
        TemplateStructureInfo with detected structure

    Raises:
        Exception: If template parsing fails

    Example:
        >>> template = '''
        ... {% for g in groups %}
        ... Region: {{ g.region }}
        ... {% for row in g.rows %}
        ... - {{ row.product }}: ${{ row.price }}
        ... {% endfor %}
        ... {% endfor %}
        ... '''
        >>> info = parse_template(template)
        >>> info.grouping_columns
        ['region']
        >>> info.row_columns
        ['product', 'price']
        >>> info.expects_groups
        True
    """
    env = Environment()

    try:
        ast = env.parse(template_str)
    except Exception as e:
        raise ValueError(f"Failed to parse Jinja template: {e}") from e

    # First, find what variable name is used for groups iteration
    # e.g., {% for g in groups %} -> group_var = 'g'
    group_var = None
    for node in ast.find_all(For):
        if isinstance(node.iter, Name) and node.iter.name == "groups":
            if isinstance(node.target, Name):
                group_var = node.target.name
                break

    # Detect if template expects 'groups' and 'rows' loops
    expects_groups = _check_for_loop_variable(ast, "groups")
    expects_rows = _check_for_loop_variable(ast, "rows")

    # Extract column references
    # For grouping columns, use the group variable name (e.g., 'g', 'group', etc.)
    if group_var:
        grouping_columns_raw = _extract_attribute_references(ast, group_var)
        # Filter out special attributes that are not DataFrame grouping columns:
        # - 'rows': structural template variable for row data
        # - 'llm_response': reserved for LLM-generated summaries
        # - 'instructions': structural template variable for group-specific instructions
        # - anything starting with '_': internal/computed variables
        grouping_columns = sorted(
            [
                col
                for col in grouping_columns_raw
                if col not in ["rows", "llm_response", "instructions"]
                and not col.startswith("_")
            ]
        )
    else:
        # Fallback to 'group' if no explicit group var found
        grouping_columns = sorted(list(_extract_attribute_references(ast, "group")))
        grouping_columns = sorted(
            [
                col
                for col in grouping_columns
                if col not in ["rows", "llm_response", "instructions"]
                and not col.startswith("_")
            ]
        )

    row_columns = sorted(list(_extract_attribute_references(ast, "row")))

    return TemplateStructureInfo(
        grouping_columns=grouping_columns,
        row_columns=row_columns,
        expects_groups=expects_groups,
        expects_rows=expects_rows,
    )


def _extract_attribute_references(node, target_var: str) -> set[str]:
    """
    Recursively extract attribute references for a specific variable.

    For example, if target_var='group', this extracts:
    - 'region' from {{ group.region }}
    - 'region' from {{ group.group.region }} (nested access)

    Args:
        node: Jinja2 AST node to traverse
        target_var: Variable name to look for (e.g., 'group', 'row')

    Returns:
        Set of attribute names referenced on the target variable
    """
    attributes = set()

    if isinstance(node, Getattr):
        # Check if this is an attribute access on our target variable
        if isinstance(node.node, Name) and node.node.name == target_var:
            attributes.add(node.attr)
        # Handle nested attributes like group.group.section
        # If node.node is also Getattr, check if it eventually resolves to target_var
        elif isinstance(node.node, Getattr):
            # Recursively extract from nested getattr
            nested_attrs = _extract_attribute_references(node.node, target_var)
            if nested_attrs:
                # If the nested part references our target, add this attr too
                attributes.add(node.attr)
        # Recursively check the node being accessed
        attributes.update(_extract_attribute_references(node.node, target_var))

    # Process all child nodes
    for child in node.iter_child_nodes():
        attributes.update(_extract_attribute_references(child, target_var))

    return attributes


def _check_for_loop_variable(node, loop_var: str) -> bool:
    """
    Check if a for-loop iterates over a specific variable.

    For example, checks if template contains {% for X in groups %}.

    Args:
        node: Jinja2 AST node to traverse
        loop_var: Variable name to look for (e.g., 'groups', 'rows')

    Returns:
        True if a for-loop over the variable is found
    """
    if isinstance(node, For):
        # Check if this for-loop iterates over our target variable
        if isinstance(node.iter, Name) and node.iter.name == loop_var:
            return True

    # Recursively check child nodes
    for child in node.iter_child_nodes():
        if _check_for_loop_variable(child, loop_var):
            return True

    return False
