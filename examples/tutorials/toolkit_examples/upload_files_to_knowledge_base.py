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

upload_content(
    user_id=user_id,
    company_id=company_id,
    content_name="upsert_json.json",
    path_to_content=str(Path(__file__).parent.parent / "data" / "upsert_json.json"),
    mime_type="text/plain",
    scope_id=scope_id,
    skip_ingestion=False,
    metadata={
        "source_owner_type": "USER",
        "scope_id": scope_id,
        "store_internally": True,
        "uploaded_by": user_id,
        "No this is not a test": "this is a test",
    },
)


# %%


chunks = search_content_chunks(
    user_id=user_id,
    company_id=company_id,
    chat_id="",
    search_string="""{
      "id": 1,
      "name": "Alice",
      "email": "alice@example.com",
      "profile": {
        "age": 30,
        "address": {
          "street": "123 Main St",
          "city": "Metropolis",
          "zip": "12345"
        },
        "preferences": ["sports", "music", "reading"]
      },
      "active": true,
      "created_at": "2023-01-01T12:00:00Z"
    }""",
    search_type=ContentSearchType.COMBINED,
    limit=10,
)
# %%
chunks[0].metadata
# %%
