# %%
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    KnowledgeBaseService,
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
# Remove specific metadata keys from all matching files
updated_contents = kb_service.remove_contents_metadata(
    keys_to_remove=["temp_status", "processing_id", "draft_version"],
    metadata_filter=metadata_filter,
)

print(f"Removed metadata from {len(updated_contents)} files")
