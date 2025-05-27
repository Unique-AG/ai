# %%
from pathlib import Path

from utilities_examples.init_sdk import init_from_env_file, unique_sdk

from unique_toolkit.content.functions import (
    ContentSearchType,
    search_content_chunks,
    upload_content,
)

company_id, user_id = init_from_env_file(Path(__file__).parent / ".." / ".env")
print(company_id, user_id)
print(unique_sdk.api_base)


scope_id = "scope_mgjzlrijadpk5q0plx242dv3"

filenames = ["upsert_text.txt", "upsert_json.json", "upsert_markdown.md"]
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

## Search chunks with metadata filter

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
# %%
print(len(chunks))

chunks[0].metadata
# %%
