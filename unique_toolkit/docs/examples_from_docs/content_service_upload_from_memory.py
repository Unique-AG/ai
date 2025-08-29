# %%
import os

from unique_toolkit import (
    ContentService,
)

# %%

content_service = ContentService.from_settings()

# %%
scope_id = os.getenv("UNIQUE_SCOPE_ID", "scope_a0478acxb2onjd6gzz8mdgdu")
content_bytes = b"Your file content here"
content = content_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"category": "documentation", "version": "1.0"},
)

# %%
