# %%
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    ContentService,
)
from unique_toolkit.content.schemas import ContentSearchType

content_service = ContentService.from_settings_filename()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
# Combined semantic and keyword search for best results
content_chunks = content_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    search_language="english",
    scope_ids=[scope_id],  # Limit to specific scopes if configured
)

print(f"Combined search found {len(content_chunks)} chunks")
