def _query_params_to_human_string(query: str, date_restrict: str | None) -> str:
    """
    Converts the WebSearchToolParameters and optional date_restrict to a human-understandable string.
    Maps date_restrict codes to human-readable periods.
    """
    query_str = f"{query}"
    if date_restrict:
        # Map date_restrict codes to human-readable strings
        mapping = {
            "d": "day",
            "w": "week",
            "m": "month",
            "y": "year",
        }
        import re

        match = re.fullmatch(r"([dwmy])(\d+)", date_restrict)
        if match:
            period, number = match.groups()
            period_str = mapping.get(period, period)
            # Pluralize if number > 1
            if number == "1":
                date_str = f"1 {period_str}"
            else:
                date_str = f"{number} {period_str}s"
        else:
            date_str = date_restrict
        query_str += f" (For the last {date_str})"
    return query_str
