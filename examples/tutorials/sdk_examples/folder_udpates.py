"""Folder Updates.

The following tutorial shows how to perform folder updates.
"""

import logging
import os
from logging import getLogger
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)


def main():
    """
    Example of updating folder ingestion config to a folder and subfolders.
    """
    import unique_sdk

    # Load environment variables
    load_dotenv(Path(__file__).parent / ".." / ".env")

    # Set up SDK configuration
    unique_sdk.api_key = os.getenv("API_KEY")
    unique_sdk.app_id = os.getenv("APP_ID")
    unique_sdk.api_base = os.getenv("API_BASE")
    company_id = os.getenv("COMPANY_ID")
    user_id = os.getenv("USER_ID")
    scope_id = os.getenv("SCOPE_ID")

    # Example: Update folder ingestion config to folder and subfolders
    try:
        folder = unique_sdk.Folder.update_ingestion_config(
            user_id=user_id,
            company_id=company_id,
            scope_id=scope_id,
            ingestionConfig={
                "chunkMaxTokens": 1898980,
                "chunkStrategy": "default",
                "uniqueIngestionMode": "standard",
            },
            applyToSubScopes=True,
        )
        logger.info(f"Folder ingestion config updated successfully: {folder}")
    except Exception as e:
        logger.error(f"Failed to update folder ingestion config: {e}")


if __name__ == "__main__":
    main()
