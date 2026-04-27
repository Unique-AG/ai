# %%
from __future__ import annotations

from unique_toolkit.experimental.content_folder import ContentFolder

folder_service = ContentFolder.from_settings()

PARENT_ROOT = "/EntangledToolkitDocs/ParentRoot"

parent_chain = folder_service.create(paths=PARENT_ROOT)
parent_scope_id = parent_chain[-1].id

nested_chain = folder_service.create(
    parent_scope_id=parent_scope_id,
    relative_path_segments=["Projects", "Scratch"],
)
leaf = nested_chain[-1]
print("parent_scope_id=", parent_scope_id)
print("leaf id=", leaf.id, "name=", leaf.name)
