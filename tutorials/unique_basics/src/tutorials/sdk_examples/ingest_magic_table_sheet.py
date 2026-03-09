"""Magic Table Sheet Ingestion
This script demonstrates how to use the Unique SDK to ingest a magic table sheet.
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
    This example demonstrates how to use the `ingest_magic_table_sheets` method to process a magic table sheet.
    The response contains a mapping of row IDs to their corresponding content IDs with the following properties:

    rowIdsToContentIds:
        A list of objects, each containing:
            rowId: The ID of the row from the magic table sheet.
            contentId: The ID of the created content associated with the row.
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

    params = {
        "user_id": user_id,
        "company_id": company_id,
        "data": [
            {
                "rowId": "2",
                "columns": [
                    {"columnId": "0", "columnName": "Section", "content": "Other"},
                    {
                        "columnId": "1",
                        "columnName": "Question",
                        "content": "What do you know?",
                    },
                    {
                        "columnId": "2",
                        "columnName": "Knowledge Base Answer",
                        "content": "Lorem Ipsum is simply dummy texktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.",
                    },
                ],
            },
        ],
        "ingestionConfiguration": {
            "columnIdsInMetadata": ["1", "2"],
            "columnIdsInChunkText": ["1", "2"],
        },
        "metadata": {
            "libraryName": "foo",
        },
        "scopeId": scope_id,
        "sheetName": "Sheet1",
    }

    created_folders = unique_sdk.Content.ingest_magic_table_sheets(**params)

    logger.info(f"created folders {created_folders}")


if __name__ == "__main__":
    main()
