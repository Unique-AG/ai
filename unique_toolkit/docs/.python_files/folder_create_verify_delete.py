# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-main>>[init]
# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-imports>>[init]
from __future__ import annotations

from unique_toolkit import ContentFolder
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-constants>>[init]
# Absolute path from the KB root; change if this collides with real data.
DEMO_FOLDER_PATH = "/EntangledToolkitDocsDemo"
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-init>>[init]
folder_service = ContentFolder.from_settings()
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-create>>[init]
created = folder_service.create_folder(path=DEMO_FOLDER_PATH)
leaf = created[-1]
print(f"Created folder id={leaf.id!r} name={leaf.name!r}")
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-verify>>[init]
info = folder_service.get_folder_info(scope_id=leaf.id)
print(
    f"Verified id={info.id!r} name={info.name!r} parent_id={info.parent_id!r} "
    f"(created as {DEMO_FOLDER_PATH!r}; compare in the UI)"
)
# Set a breakpoint here (IDE or `breakpoint()`) to inspect `info` and confirm in the UI.
# ~/~ end

# ~/~ begin <<docs/modules/examples/content/content-folder.md#folder-mgmt-delete>>[init]
delete_result = folder_service.delete_folder(scope_id=leaf.id)
print(
    "Deleted:",
    delete_result.get("successFolders"),
    "Failed:",
    delete_result.get("failedFolders"),
)
# ~/~ end
# ~/~ end
