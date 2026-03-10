import os
from pathlib import Path

from dotenv import load_dotenv

import unique_sdk


def init_from_env_file(filepath: Path) -> tuple[str, str]:
    """Initialize the SDK from the environment file.

    Args:
        filepath: The path to the environment file.

    Returns:
        A tuple containing the company ID and user ID.
    """
    load_dotenv(filepath)
    unique_sdk.api_key = os.getenv("API_KEY", "")
    unique_sdk.app_id = os.getenv("APP_ID", "")
    unique_sdk.api_base = os.getenv("API_BASE", "")
    company_id = os.getenv("COMPANY_ID", "")
    user_id = os.getenv("USER_ID", "")

    return company_id, user_id
