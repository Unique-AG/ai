import os
import tempfile
from pathlib import Path

import requests

import unique_sdk


# download readUrl a random directory in /tmp
def download_file(url: str, filename: str):
    # Ensure the URL is a valid string
    if not isinstance(url, str):
        raise ValueError("URL must be a string.")

    # Create a random directory inside /tmp
    random_dir = tempfile.mkdtemp(dir="/tmp")

    # Create the full file path
    file_path = Path(random_dir) / filename

    # Download the file and save it to the random directory
    response = requests.get(url)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            file.write(response.content)
    else:
        raise Exception(f"Error downloading file: Status code {response.status_code}")

    return file_path


def upload_file(
    userId,
    companyId,
    path_to_file,
    displayed_filename,
    mime_type,
    scope_or_unique_path=None,
    chat_id=None,
):
    size = os.path.getsize(path_to_file)
    createdContent = unique_sdk.Content.upsert(
        user_id=userId,
        company_id=companyId,
        input={
            "key": displayed_filename,
            "title": displayed_filename,
            "mimeType": mime_type,
        },
        scopeId=scope_or_unique_path,
        chatId=chat_id,
    )

    uploadUrl = createdContent.writeUrl

    # upload to azure blob storage SAS url uploadUrl the pdf file translatedFile make sure it is treated as a application/pdf
    with open(path_to_file, "rb") as file:
        requests.put(
            uploadUrl,
            data=file,
            headers={
                "X-Ms-Blob-Content-Type": mime_type,
                "X-Ms-Blob-Type": "BlockBlob",
            },
        )

    unique_sdk.Content.upsert(
        user_id=userId,
        company_id=companyId,
        input={
            "key": displayed_filename,
            "title": displayed_filename,
            "mimeType": mime_type,
            "byteSize": size,
        },
        scopeId=scope_or_unique_path,
        fileUrl=createdContent.readUrl,
        chatId=chat_id,
    )

    return createdContent


def download_content(
    companyId: str, userId: str, content_id: str, filename: str, chat_id: str = None
):
    # Ensure the URL is a valid string
    if not isinstance(content_id, str):
        raise ValueError("URL must be a string.")

    url = f"{unique_sdk.api_base}/content/{content_id}/file"
    if chat_id:
        url = f"{url}?chatId={chat_id}"
    print(url)

    # Create a random directory inside /tmp
    random_dir = tempfile.mkdtemp(dir="/tmp")

    # Create the full file path
    file_path = Path(random_dir) / filename

    # Download the file and save it to the random directory
    headers = {
        "x-api-version": unique_sdk.api_version,
        "x-app-id": unique_sdk.app_id,
        "x-user-id": userId,
        "x-company-id": companyId,
        "Authorization": "Bearer %s" % (unique_sdk.api_key,),
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            file.write(response.content)
    else:
        raise Exception(f"Error downloading file: Status code {response.status_code}")

    return file_path
