"""Rule-based searches.

The following tutorial shows how to perform rule-based search.
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
    Example of retrieving chunks based on a metadata filter search.
    This example assumes that the content has been previously uploaded and indexed.
    The search is performed using the `Content.get_info` method, which returns a list of content items
    that match the specified metadata filter.
    The content is then retrieved using the `Content.get` method, which returns the content object
    with the specified content ID.
    The content object contains a list of chunks, which are the individual pieces of content
    that match the search criteria.
    """
    import unique_sdk

    # Load environment variables
    load_dotenv(Path(__file__).parent / ".." / ".env")

    # Set up SDK configuration
    unique_sdk.api_key = os.getenv("API_KEY", "")
    unique_sdk.app_id = os.getenv("APP_ID", "")
    unique_sdk.api_base = os.getenv("API_BASE", "")
    company_id = os.getenv("COMPANY_ID", "")
    user_id = os.getenv("USER_ID", "")

    # Define a rule for the search
    metadata_filter = {
        "or": [
            {
                "and": [
                    {
                        "operator": "contains",
                        "path": ["folderIdPath"],
                        "value": "uniquepathid://",
                    },
                    {"operator": "contains", "path": ["title"], "value": "i"},
                ]
            }
        ]
    }

    content_info_result = unique_sdk.Content.get_info(
        user_id=user_id,
        company_id=company_id,
        metadataFilter=metadata_filter,
        skip=0,
        take=3,
    )

    logger.info(f"Total count: {content_info_result['totalCount']}")
    for item in content_info_result["contentInfos"]:
        content = unique_sdk.Content.search(
            user_id=user_id,
            company_id=company_id,
            where={
                "id": {
                    "equals": item["id"],
                }
            },
        )
        firstContent = content[0] if content else None
        if not firstContent:
            logger.warning(f"No content found for ID: {item['id']}")
            continue
        logger.info(
            f"Content ID: {firstContent.id}, Key: {firstContent.key}, Chunks Len: {len(firstContent.chunks)}"
        )


if __name__ == "__main__":
    main()
