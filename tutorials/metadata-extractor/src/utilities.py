import re
from datetime import datetime
from typing import Dict, Optional


def find_topic(title: str | None) -> str:
    if not title:
        return ""

    # For filenames like "TEST_PDF_2025-02-18_Market themes and report 2.18.2025.pdf"
    # Look for text after a date pattern
    topic_match = re.search(r"\d{4}-\d{2}-\d{2}_([^_]+)", title)
    if topic_match:
        # Extract the topic and remove everything from the first number onwards
        topic = re.sub(r"\s*\d.*$", "", topic_match.group(1)).strip()
        return topic.lower()

    # For filenames like "20241028_Boeing_Stock_Sale_Buys_Multiple_Quarters-_Dilutes_Heavily-_React.pdf"
    # Look for text between the first underscore and first hyphen
    topic_match = re.search(r"\d{8}_([^-]+)-", title)
    if topic_match:
        topic = topic_match.group(1).strip()
        return topic.lower()

    return ""


def internal_to_iso_date(date: str) -> str:
    dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_hyphenated_date(date_str: str) -> Optional[Dict[str, int]]:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        year, month, day = date_str.split("-")
        return {"year": int(year), "month": int(month), "day": int(day)}
    except (ValueError, IndexError):
        return None


def parse_compact_date(date_str: str) -> Optional[Dict[str, int]]:
    """Parse a date string in YYYYMMDD format."""
    try:
        if len(date_str) != 8:
            return None
        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        return {"year": year, "month": month, "day": day}
    except ValueError:
        return None


def is_valid_date(year: int, month: int, day: int) -> bool:
    """Check if the given year, month, day represent a valid date."""
    # Basic range checks
    if year < 1000 or year > 9999:
        return False
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False

    # Create date and check if it matches input (catches invalid dates like Feb 30)
    try:
        date = datetime(year, month, day)
        return date.year == year and date.month == month and date.day == day
    except ValueError:
        return False


def to_iso_date(year: int, month: int, day: int) -> str:
    """Convert year, month, day to ISO date string."""
    return datetime(year, month, day).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_date_from_filename(filename: Optional[str]) -> Optional[str]:
    """Extract and validate a date from a filename, returning ISO format or None."""
    if not filename:
        return None

    # Date extractor configurations matching JavaScript logic
    date_extractors = [
        {"regex": re.compile(r"(\d{4}-\d{2}-\d{2})"), "parser": parse_hyphenated_date},
        {"regex": re.compile(r"(\d{8})"), "parser": parse_compact_date},
    ]

    for extractor in date_extractors:
        date_match = extractor["regex"].search(filename)
        if date_match:
            date_str = date_match.group(1)
            parsed = extractor["parser"](date_str)
            if parsed and is_valid_date(parsed["year"], parsed["month"], parsed["day"]):
                return to_iso_date(parsed["year"], parsed["month"], parsed["day"])

    return None


def find_date(title: str | None, default_date: str) -> str:
    """Find a date in the title, falling back to default_date if none found."""
    if not title:
        return default_date

    extracted_date = get_date_from_filename(title)
    return extracted_date if extracted_date else default_date
