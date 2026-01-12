"""Template handler service."""

from jinja2 import Template, TemplateError

from unique_toolkit._common.experimental.write_up_agent.schemas import (
    GroupData,
    ProcessedGroup,
)
from unique_toolkit._common.experimental.write_up_agent.services.dataframe_handler.utils import (
    from_snake_case_to_display_name,
)
from unique_toolkit._common.experimental.write_up_agent.services.template_handler.exceptions import (
    ColumnExtractionError,
    TemplateParsingError,
    TemplateRenderingError,
    TemplateStructureError,
)
from unique_toolkit._common.experimental.write_up_agent.services.template_handler.utils import (
    parse_template,
)


# TODO [UN-16142]: Simplify template logic
class TemplateHandler:
    """
    Handles all template operations.

    Responsibilities:
    - Extract grouping column (single only)
    - Extract selected columns
    - Render template for groups
    """

    def __init__(self, template: str):
        """
        Initialize template handler.

        Args:
            template: Jinja template string

        Raises:
            TemplateParsingError: If template cannot be parsed
        """
        self._template = template

        try:
            self._jinja_template = Template(template, lstrip_blocks=True)
        except TemplateError as e:
            snippet = template[:100] + "..." if len(template) > 100 else template
            raise TemplateParsingError(
                f"Failed to parse Jinja template: {e}", template_snippet=snippet
            ) from e

        self._parsed_info = None

    def _get_parsed_info(self):
        """
        Lazy parse template.

        Raises:
            TemplateParsingError: If template structure cannot be parsed
        """
        if self._parsed_info is None:
            try:
                self._parsed_info = parse_template(self._template)
            except Exception as e:
                raise TemplateParsingError(
                    f"Failed to parse template structure: {e}"
                ) from e
        return self._parsed_info

    def get_grouping_column(self) -> str:
        """
        Extract the single grouping column.

        Returns:
            Column name to group by

        Raises:
            TemplateStructureError: If template structure is invalid
            ColumnExtractionError: If grouping column detection fails
        """
        info = self._get_parsed_info()

        if not info.expects_groups:
            raise TemplateStructureError(
                "Template must use grouping pattern: {% for g in groups %}",
                expected_structure="{% for g in groups %}",
            )

        if len(info.grouping_columns) == 0:
            raise ColumnExtractionError(
                "No grouping column detected in template. Use {{ g.column_name }} to reference grouping columns."
            )

        if len(info.grouping_columns) > 1:
            raise ColumnExtractionError(
                f"Single grouping column required. Found {len(info.grouping_columns)}: {info.grouping_columns}",
                detected_columns=info.grouping_columns,
            )

        return info.grouping_columns[0]

    def get_selected_columns(self) -> list[str]:
        """
        Extract columns referenced in template.

        Returns:
            List of column names from {{ row.column }} patterns
        """
        info = self._get_parsed_info()
        return info.row_columns

    def render_group(
        self, group_data: GroupData, llm_response: str | None = None
    ) -> str:
        """
        Render template for a single group.

        This method supports two rendering modes:
        1. Without llm_response: Renders the full row data (for LLM input)
        2. With llm_response: Renders the LLM output instead of row data (for final report)

        Args:
            group_data: GroupData instance with group_key and rows
            llm_response: Optional LLM-generated output. If provided, the template
                         will render this instead of the detailed row loop.

        Returns:
            Rendered template string

        Raises:
            TemplateRenderingError: If rendering fails
        """
        try:
            grouping_column = self.get_grouping_column()

            # Prepare group item with grouping column value, rows, and llm_response
            group_item = {
                grouping_column: from_snake_case_to_display_name(group_data.group_key),
                "rows": group_data.rows,
                "llm_response": llm_response,  # Add to group item, not top level
            }

            # Render with groups list (template expects {% for g in groups %})
            return self._jinja_template.render(groups=[group_item])
        except (TemplateError, KeyError) as e:
            context_keys = ["group_key", "rows", "llm_response"]
            raise TemplateRenderingError(
                f"Failed to render template: {e}", context_keys=context_keys
            ) from e

    def render_all_groups(self, processed_groups: list[ProcessedGroup]) -> str:
        """
        Render template for all groups at once.

        Takes advantage of the template's {% for g in groups %} loop
        to render all groups in a single pass.

        Args:
            processed_groups: List of ProcessedGroup instances with group_key, rows, and llm_response

        Returns:
            Rendered template string with all groups

        Raises:
            TemplateRenderingError: If rendering fails
        """
        try:
            grouping_column = self.get_grouping_column()

            # Prepare all groups for rendering
            groups_data = []
            for group_data in processed_groups:
                # Convert snake_case group_key to Title Case for display
                display_group_key = from_snake_case_to_display_name(
                    group_data.group_key
                )

                group_item = {
                    grouping_column: display_group_key,  # Use Title Case for display
                    "rows": group_data.rows,
                    "llm_response": group_data.llm_response,
                }
                groups_data.append(group_item)

            # Render all groups at once using template's loop
            return self._jinja_template.render(groups=groups_data)

        except (TemplateError, KeyError) as e:
            raise TemplateRenderingError(f"Failed to render all groups: {e}") from e
