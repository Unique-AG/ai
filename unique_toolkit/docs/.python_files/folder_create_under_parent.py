# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-main-nested>>[init]
# ~/~ begin <<docs/setup/_script_dependencies.md#example-script-deps>>[init]
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-imports>>[init]
from __future__ import annotations

from unique_toolkit.experimental.resources.content_folder import ContentFolder
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-init>>[init]
folder_service = ContentFolder.from_settings()
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-constants-nested>>[init]
PARENT_ROOT = "/EntangledToolkitDocs/ParentRoot"
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-create-nested-under-parent>>[init]
parent_chain = folder_service.create(paths=PARENT_ROOT)
parent_scope_id = parent_chain[-1].id

nested_chain = folder_service.create(
    parent_scope_id=parent_scope_id,
    relative_path_segments=["Projects", "Scratch"],
)
leaf = nested_chain[-1]
print("parent_scope_id=", parent_scope_id)
print("leaf id=", leaf.id, "name=", leaf.name)
# ~/~ end
# ~/~ end
