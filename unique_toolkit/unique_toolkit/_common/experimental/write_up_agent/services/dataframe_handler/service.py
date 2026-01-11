"""DataFrame handler service."""

import pandas as pd

from unique_toolkit._common.experimental.write_up_agent.schemas import GroupData
from unique_toolkit._common.experimental.write_up_agent.services.dataframe_handler.exceptions import (
    DataFrameGroupingError,
    DataFrameProcessingError,
    DataFrameValidationError,
)
from unique_toolkit._common.experimental.write_up_agent.services.dataframe_handler.utils import (
    dataframe_to_dict_records,
    normalize_column_names,
)


class DataFrameHandler:
    """
    Handles all DataFrame operations.

    This handler automatically converts all column names to snake_case to ensure
    compatibility with Jinja template syntax. For example:
    - "My Column" becomes "my_column"
    - "UserName" becomes "user_name"
    - "column-name" becomes "column_name"

    This normalization happens automatically during validation and grouping operations.

    Responsibilities:
    - Normalize column names to snake_case
    - Validate DataFrame has required columns
    - Create groups from DataFrame
    """

    def validate_columns(
        self, df: pd.DataFrame, grouping_column: str, selected_columns: list[str]
    ) -> None:
        """
        Validate DataFrame has required columns.

        NOTE: Column names are automatically converted to snake_case before validation.
        Ensure your template uses snake_case column references (e.g., {{ row.my_column }}).

        Args:
            df: pandas DataFrame to validate
            grouping_column: Column to group by (should be in snake_case)
            selected_columns: Columns that should exist (should be in snake_case)

        Raises:
            DataFrameValidationError: If columns are missing after normalization

        Example:
            >>> df = pd.DataFrame({"My Section": [1], "My Question": [2]})
            >>> handler.validate_columns(df, "my_section", ["my_question"])
            # Validation passes because "My Section" -> "my_section"
        """
        # Normalize DataFrame columns to snake_case
        normalized_df = normalize_column_names(df)

        required_columns = {grouping_column} | set(selected_columns)
        missing_columns = required_columns - set(normalized_df.columns)

        if missing_columns:
            raise DataFrameValidationError(
                f"DataFrame missing required columns after snake_case normalization: {sorted(missing_columns)}. "
                f"Available columns: {sorted(normalized_df.columns)}",
                missing_columns=sorted(missing_columns),
            )

    def create_groups(
        self, df: pd.DataFrame, grouping_column: str, selected_columns: list[str]
    ) -> list[GroupData]:
        """
        Create groups from DataFrame.

        NOTE: Column names are automatically converted to snake_case.
        The returned GroupData instances will have snake_case column names in their rows.

        IMPORTANT: Groups are returned in the order of their first appearance in the DataFrame,
        NOT sorted alphabetically. This preserves the logical flow of your data.

        Args:
            df: pandas DataFrame to group
            grouping_column: Column to group by (should be in snake_case)
            selected_columns: Columns to include in rows (should be in snake_case)

        Returns:
            List of GroupData instances in order of first appearance, each containing
            group_key and rows with snake_case columns

        Raises:
            DataFrameGroupingError: If grouping fails
            DataFrameProcessingError: If data processing fails

        Example:
            >>> df = pd.DataFrame({
            ...     "My Section": ["Intro", "Methods", "Results", "Intro"],
            ...     "My Question": ["Q1", "Q2", "Q3", "Q4"],
            ... })
            >>> groups = handler.create_groups(df, "my_section", ["my_question"])
            >>> [g.group_key for g in groups]
            ['Intro', 'Methods', 'Results']  # Order preserved, not alphabetical
        """
        # Normalize column names to snake_case
        normalized_df = normalize_column_names(df)

        if grouping_column not in normalized_df.columns:
            raise DataFrameGroupingError(
                f"Grouping column '{grouping_column}' not found in normalized DataFrame. "
                f"Available columns: {sorted(normalized_df.columns)}",
                grouping_column=grouping_column,
            )

        try:
            # Use sort=False to preserve the order of first appearance in the DataFrame
            grouped = normalized_df.groupby(grouping_column, sort=False)
        except Exception as e:
            raise DataFrameGroupingError(
                f"Failed to group DataFrame by '{grouping_column}': {e}",
                grouping_column=grouping_column,
            ) from e

        results = []

        try:
            for group_key, group_df in grouped:
                # Filter columns if specified
                if selected_columns:
                    cols_to_use = [c for c in selected_columns if c in group_df.columns]
                    limited_df = group_df.loc[:, cols_to_use]
                else:
                    limited_df = group_df

                # Convert to dict records
                rows = dataframe_to_dict_records(limited_df)

                # Create GroupData instance with proper typing
                results.append(GroupData(group_key=str(group_key), rows=rows))
        except Exception as e:
            raise DataFrameProcessingError(f"Error processing grouped data: {e}") from e

        return results
