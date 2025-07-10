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
    unique_sdk.api_key = "ukey_ph_0d_gNdjf6I5us3_p8Zz_qHp8Fj0UE7Fvq7I-KZOY"

    # os.getenv("API_KEY")
    unique_sdk.app_id = "app_yxpvfu0mzt4qkta56r9zv248" # os.getenv("APP_ID")
    # unique_sdk.api_base = os.getenv("API_BASE")
    company_id = "237521044380848186" # os.getenv("COMPANY_ID")
    user_id = "327965239901425761" #os.getenv("USER_ID")
    print('##############')
    print(os.getenv("API_KEY"))

    print("API_KEY:", os.getenv("API_KEY"))
    print("APP_ID:", os.getenv("APP_ID"))
    print("API_BASE:", os.getenv("API_BASE"))
    print("COMPANY_ID:", os.getenv("COMPANY_ID"))
    print("USER_ID:", os.getenv("USER_ID"))

    # params = {
    #     "user_id": user_id,
    #     "company_id": company_id,
    #     "paths": ["/unique/path1", "/unique/path2"],
    # }

    # params = {
    #     "prompt": "Summarize the following text.",
    #     "chatId": "assistant_v09biqwriqkhqykv41m0nkzo",
    #     "messages": [
    #         {"role": "user", "content": "What is the weather today?"}
    #     ],
    #     "languageModel": "AZURE_GPT_4_0613"
    # }
    # 
    # unique_sdk.SearchString.create(user_id=user_id, company_id=company_id, **params)


    unique_sdk.api_base = "https://gateway.oleole.unique.app/public/chat"
    

    unique_sdk.Folder.create_paths(
        user_id=user_id,
        company_id=company_id,
        paths=[f"/stress_test/path{i}" for i in range(3001, 3500)],
    )

    # created_folders = unique_sdk.Folder.create_paths(**params)

    # logger.info(f"created folders {created_folders}")


if __name__ == "__main__":
    main()
