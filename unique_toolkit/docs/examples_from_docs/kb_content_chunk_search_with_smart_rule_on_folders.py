# %%
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    KnowledgeBaseService,
)
from unique_toolkit.content.schemas import (
    ContentSearchType,
)
from unique_toolkit.smart_rules.compile import (
    Operator,
    Statement,
)

kb_service = KnowledgeBaseService.from_settings()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
smart_rule_folder_content = Statement(
    operator=Operator.EQUALS, value=f"{scope_id}", path=["folderId"]
)

metadata_filter = smart_rule_folder_content.model_dump(mode="json")


content_chunks = kb_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    metadata_filter=metadata_filter,
)
