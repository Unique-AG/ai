# %%
import io
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    KnowledgeBaseService,
)

kb_service = KnowledgeBaseService.from_settings()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
content_id = demo_env_vars.get("UNIQUE_CONTENT_ID") or "unknown"
# Download content as bytes
content_bytes = kb_service.download_content_to_bytes(
    content_id=content_id or "unknown",
)

# Process in memory
text = ""
with io.BytesIO(content_bytes) as file_like:
    text = file_like.read().decode("utf-8")

print(text)
