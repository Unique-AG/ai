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
    Example of creating folders based on specified paths.
    This example demonstrates how to create folders using the `Folder.create` method.
    The method takes parameters such as user_id, company_id, and a list of folder paths to be created.
    The create method returns a dictionary containing a key createdFolders, which holds a list of CreatedFolder objects. Each CreatedFolder object includes the following attributes:
    
    id: A string representing the unique identifier of the folder.
    object: A string indicating the type of the object (e.g., "folder").
    name: A string representing the name of the folder.
    parentId: An optional string representing the ID of the parent folder, if any.
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

    params = {
        "user_id": user_id,
        "company_id": company_id,
        "paths": ["/unique/path1", "/unique/path2"],
    }

    created_folders = unique_sdk.Folder.create_paths(**params)

    logger.info(f"created folders {created_folders}")

if __name__ == "__main__":
    main()