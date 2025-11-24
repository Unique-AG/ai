# %%
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    KnowledgeBaseService,
)

kb_service = KnowledgeBaseService.from_settings()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
file_path = Path(__file__).parent / "test.txt"
# Configure ingestion settings
content = kb_service.upload_content(
    path_to_content=str(file_path),
    content_name=Path(file_path).name,
    mime_type="text/plain",
    scope_id=scope_id,
    skip_ingestion=False,  # Process the content for search
    metadata={"department": "story", "classification": "public"},
)

# %%
