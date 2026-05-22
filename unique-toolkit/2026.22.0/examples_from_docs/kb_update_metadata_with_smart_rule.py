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
# Update metadata for all files matching the filter
updated_contents = kb_service.update_contents_metadata(
    additional_metadata={
        "department": "legal",
        "classification": "confidential",
        "last_reviewed": "2025-01-01",
    },
    metadata_filter=metadata_filter,
)

print(f"Updated metadata for {len(updated_contents)} files")
