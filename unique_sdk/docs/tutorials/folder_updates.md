# Folder Updates Tutorial

This tutorial demonstrates how to perform folder updates, including updating ingestion configurations and managing folder access permissions.

## Overview

Learn how to:

- Update folder ingestion configurations
- Apply changes to subfolders
- Add and remove folder access permissions

## Prerequisites

- Unique SDK installed and configured
- Valid API credentials (`API_KEY`, `APP_ID`)
- Environment variables set (`COMPANY_ID`, `USER_ID`, `SCOPE_ID`, `FOLDER_PATH`)

## Complete Example

### Full Folder Update Example

```python
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
    Example of updating folder ingestion config of a folder and its subfolders.
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
    folder_path = os.getenv("FOLDER_PATH")

    # Example: Update folder ingestion config to folder and subfolders based on the path
    try:
        folder = unique_sdk.Folder.update_ingestion_config(
            user_id=user_id,
            company_id=company_id,
            folderPath=folder_path,
            ingestionConfig={
                "chunkMaxTokens": 1000,
                "chunkStrategy": "default",
                "uniqueIngestionMode": "standard",
            },
            applyToSubScopes=True,
        )
        logger.info(f"Folder ingestion config updated successfully: {folder}")
    except Exception as e:
        logger.error(f"Failed to update folder ingestion config: {e}")

    # Example: Add access to a folder
    try:
        folder = unique_sdk.Folder.add_access(
            user_id=user_id,
            company_id=company_id,
            scopeId=scope_id,
            scopeAccesses=[
                {
                    "entityId": "group_id",
                    "type": "WRITE",
                    "entityType": "GROUP",
                }
            ],
            applyToSubScopes=True,
        )
        logger.info(f"Access added successfully: {folder}")
    except Exception as e:
        logger.error(f"Failed to add access: {e}")

    # Example: Remove access from a folder
    try:
        folder = unique_sdk.Folder.remove_access(
            user_id=user_id,
            company_id=company_id,
            scopeId=scope_id,
            scopeAccesses=[
                {
                    "entityId": "group_id",
                    "type": "WRITE",
                    "entityType": "GROUP",
                }
            ],
            applyToSubScopes=True,
        )
        logger.info(f"Access removed successfully: {folder}")
    except Exception as e:
        logger.error(f"Failed to remove access: {e}")


if __name__ == "__main__":
    main()
```

## Related Resources

- [Folder API](../api_resources/folder.md) - Complete Folder API documentation
- [Configuration Guide](../getting_started/configuration.md) - Set up your environment
