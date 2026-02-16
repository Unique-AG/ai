# %%
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    KnowledgeBaseService,
)
from unique_toolkit.smart_rules.compile import (
    AndStatement,
    Operator,
    Statement,
)

kb_service = KnowledgeBaseService.from_settings()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
content_bytes = b"Your file content here"
content = kb_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document_custom.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"customMetaData": "customValue", "version": "1.0"},
)
content_bytes = b"Your file content here"
content = kb_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"category": "documentation", "version": "1.0"},
)
smart_rule_custom = Statement(
    operator=Operator.EQUALS, value="customValue", path=["customMetaData"]
)

metadata_filter = smart_rule_custom.model_dump(mode="json")
smart_rule_folder_content = Statement(
    operator=Operator.EQUALS, value=f"{scope_id}", path=["folderId"]
)

metadata_filter = smart_rule_folder_content.model_dump(mode="json")
smart_rule_folders_and_mime = AndStatement(
    and_list=[smart_rule_folder_content, smart_rule_custom]
)
metadata_filter = smart_rule_folders_and_mime.model_dump(mode="json")
kb_service.delete_contents(metadata_filter=metadata_filter)
