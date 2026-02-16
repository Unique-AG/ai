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
smart_rule_custom = Statement(
    operator=Operator.EQUALS, value="customValue", path=["customMetaData"]
)

metadata_filter = smart_rule_custom.model_dump(mode="json")
infos = kb_service.get_paginated_content_infos(metadata_filter=metadata_filter)
