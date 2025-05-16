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
    import unique_sdk

    # Load environment variables
    load_dotenv(Path(__file__).parent / ".." / ".env")

    # Set up SDK configuration
    unique_sdk.api_key = os.getenv("API_KEY", "dummy")
    unique_sdk.app_id = os.getenv("APP_ID", "dummy")
    unique_sdk.api_base = os.getenv("API_BASE", "dummy")
    company_id = os.getenv("COMPANY_ID", "dummy")
    user_id = os.getenv("USER_ID", "dummy")

    # Define a rule for the search
    rule = {
        "or": [
            {
                "and": [
                    {
                        "operator": "contains",
                        "path": ["folderIdPath"],
                        "value": "uniquepathid://scope_test_id",
                    },
                    {"operator": "contains", "path": ["testtttt"], "value": "superrrr"},
                ]
            }
        ]
    }

    # Perform the rule-based search
    result = unique_sdk.Content.rule_search(
        user_id=user_id,
        company_id=company_id,
        rule=rule,
        skip=0,
        take=10,
    )

    # Log the results
    logger.info(f"Search completed with {len(result['nodes'])} nodes.")
    logger.info(f"Total count: {result['totalCount']}")
    for node in result["nodes"]:
        logger.info(f"Node ID: {node['id']}, Key: {node['key']}")


if __name__ == "__main__":
    main()
