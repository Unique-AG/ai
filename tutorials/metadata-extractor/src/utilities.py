import re
from datetime import datetime


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


def find_date(title: str | None) -> str:
    if not title:
        return ""

    # Check for standard date format YYYY-MM-DD
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
    if date_match:
        date_str = date_match.group(1)
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return ""

    # Check for date format YYYYMMDD without separators
    date_match = re.search(r"(\d{8})_", title)
    if date_match:
        date_str = date_match.group(1)
        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return ""

    return ""
