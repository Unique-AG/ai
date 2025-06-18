# %%
from pathlib import Path

from utilities_examples.init_sdk import init_from_env_file

from unique_toolkit.content.functions import (
    ContentSearchType,
    search_content_chunks,
    upload_content,
)

# Init sdk, company_id, user_id are necessary for auth
company_id, user_id = init_from_env_file(Path(__file__).parent / ".." / ".env")

# Scope to upload to
scope_id = "scope_mgjzlrijadpk5q0plx242dv3"

# Files to upload to the knowledgebase
filenames = ["upsert_text.txt", "upsert_json.json", "upsert_markdown.md"]

# Note that a json can be uploaded as plain text
mimetypes = ["text/plain", "text/plain", "text/markdown"]

for filename, mimetype in zip(filenames, mimetypes):
    print(f"Uploading {filename} with mimetype {mimetype}")
    result = upload_content(
        user_id=user_id,
        company_id=company_id,
        content_name=filename,
        path_to_content=str(Path(__file__).parent.parent / "data" / filename),
        mime_type=mimetype,
        scope_id=scope_id,
        skip_ingestion=False,
        metadata={
            "source_owner_type": "USER",
            "scope_id": scope_id,
            "store_internally": True,
            "uploaded_by": user_id,
            "filename": filename,
        },
    )

    print(result)


# %%

# Search chunks with metadata filter

# The metadata_filter is a powerful tool to filter across the knowledge base. It can be defined
# directly here in python. Additionally it can be defined in the space configuration of the frontend
# and shipped with the event to the python webhook via the event. This allows to create flexible knowledge
# on each space.

# More on the metadata_filter and smart rules
# https://unique-ch.atlassian.net/wiki/spaces/PUB/pages/844333081/Smart+Rules+and+Dynamic+Parameters

# More on the unique query language and the metadata filter can be found here
# https://unique-ch.atlassian.net/wiki/spaces/PUB/pages/488079474/Extended+Search+with+UniqueQL+on+Metadata


metadata_filter = {
    "operator": "contains",
    "path": ["filename"],
    "value": ".json",
}


chunks = search_content_chunks(
    user_id=user_id,
    company_id=company_id,
    chat_id="",
    scope_ids=[scope_id],
    search_string="Alice",
    search_type=ContentSearchType.COMBINED,
    limit=10,
    metadata_filter=metadata_filter,
)
print(len(chunks))
chunks[0].metadata
