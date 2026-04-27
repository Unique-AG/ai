# %%
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    KnowledgeBaseService,
)

kb_service = KnowledgeBaseService.from_settings()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
# Search for specific content files
contents = kb_service.search_contents(
    where={"title": {"contains": "manual"}},
)
