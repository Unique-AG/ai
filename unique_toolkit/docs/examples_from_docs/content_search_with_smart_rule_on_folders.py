# %%
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    ContentService,
)
from unique_toolkit.content.schemas import (
    ContentSearchType,
)
from unique_toolkit.smart_rules.compile import (
    Operator,
    Statement,
)

content_service = ContentService.from_settings()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
smart_rule_folder_content = Statement(
    operator=Operator.EQUALS, value=f"{scope_id}", path=["folderIdPath"]
)


content_chunks = content_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    search_language="english",
    metadata_filter=smart_rule_folder_content.model_dump(mode="json"),
)

