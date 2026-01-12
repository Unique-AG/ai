"""Utility functions for DataFrame operations."""

import re

import pandas as pd


def to_snake_case(text: str) -> str:
    """
    Convert a string to snake_case.

    This ensures column names are compatible with Jinja template syntax.

    Examples:
        >>> to_snake_case("MyColumn")
        'my_column'
        >>> to_snake_case("my_column")
        'my_column'
        >>> to_snake_case("My Column Name")
        'my_column_name'
        >>> to_snake_case("column-name")
        'column_name'
        >>> to_snake_case("Column_123")
        'column_123'

    Args:
        text: String to convert

    Returns:
        snake_case version of the string
    """
    # Replace spaces and hyphens with underscores
    text = text.replace(" ", "_").replace("-", "_")

    # Insert underscore before uppercase letters (for camelCase/PascalCase)
    text = re.sub(r"(?<!^)(?=[A-Z])", "_", text)

    # Convert to lowercase
    text = text.lower()

    # Remove duplicate underscores
    text = re.sub(r"_+", "_", text)

    # Remove leading/trailing underscores
    text = text.strip("_")

    return text


def from_snake_case_to_display_name(text: str) -> str:
    """
    Convert snake_case text back to Title Case for display.

    Args:
        text: snake_case text to convert

    Returns:
        Title Case version of the text

    Example:
        >>> from_snake_case("executive_summary")
        'Executive Summary'
        >>> from_snake_case("my_column_name")
        'My Column Name'
        >>> from_snake_case("api_design")
        'Api Design'
    """
    # Split on underscores and capitalize each word
    words = text.split("_")
    return " ".join(word.capitalize() for word in words)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert all DataFrame column names to snake_case.

    This normalization ensures column names are compatible with Jinja template
    syntax (e.g., {{ row.my_column }} works, but {{ row.My Column }} doesn't).

    Examples:
        >>> df = pd.DataFrame({"My Column": [1], "AnotherColumn": [2]})
        >>> normalized = normalize_column_names(df)
        >>> list(normalized.columns)
        ['my_column', 'another_column']

    Args:
        df: Input DataFrame

    Returns:
        New DataFrame with normalized column names
    """
    ## TODO [UN-16142]: Normalization may lead to duplicate column names, we should handle this case
    normalized_columns = {col: to_snake_case(col) for col in df.columns}
    return df.rename(columns=normalized_columns)


def limit_dataframe_rows(df: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    """
    Limit DataFrame to first N rows.

    Args:
        df: DataFrame to limit
        max_rows: Maximum number of rows

    Returns:
        DataFrame with at most max_rows rows
    """
    if len(df) <= max_rows:
        return df.copy()
    return df.head(max_rows).copy()


def dataframe_to_dict_records(
    df: pd.DataFrame, columns: list[str] | None = None
) -> list[dict]:
    """
    Convert DataFrame to list of dict records.

    Args:
        df: DataFrame to convert
        columns: Optional list of columns to include

    Returns:
        List of dict records
    """
    if columns:
        df = df.loc[:, columns]

    # Replace NaN with None for better serialization
    return df.where(pd.notna(df), None).to_dict(orient="records")
