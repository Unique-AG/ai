# %%
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    ContentService,
)
from unique_toolkit.content.schemas import ContentSearchType

content_service = ContentService.from_settings()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
# Search for content using vector similarity
content_chunks = content_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.VECTOR,
    limit=10,
    score_threshold=0.7,  # Only return results with high similarity
    scope_ids=[scope_id],
)

print(f"Found {len(content_chunks)} relevant chunks")
for i, chunk in enumerate(content_chunks[:3]):
    print(f"  {i + 1}. {chunk.text[:100]}...")
